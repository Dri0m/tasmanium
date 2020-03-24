import http.server
import multiprocessing as mp
import os
import socketserver
from typing import List, AnyStr, Dict, Any

import click
import cucumber_tag_expressions

from tasmanium import logger
from tasmanium.boiled_pickle import Feature, _register_environment, Scenario, Context
from tasmanium.html_reporter.html_reporter import generate_html_report
from tasmanium.registrars import before_all, after_all
from tasmanium.utils import _glob_feature_files_in_paths, _import_submodules

l = logger.getLogger(__name__)


def register_steps():
    """Import all steps so that decorators on them run and the step functions are registered."""
    l.ttrace("registering steps...")
    _import_submodules('steps')
    l.ttrace("steps registered")


def filter_by_tags(features: List[Feature], summary: Dict[AnyStr, Any], user_flat_tag_expr: AnyStr, user_feature_tag_expr: AnyStr,
                   user_scenario_tag_expr: AnyStr,
                   user_example_tag_expr: AnyStr) -> List[Feature]:
    l.ttrace("checking user tag filters...")
    if user_flat_tag_expr != "":
        l.ttrace("filter tests by flat tags...")
        user_expr = cucumber_tag_expressions.TagExpressionParser.parse(user_flat_tag_expr)
        l.ttrace(f"user flat tag expression: '{user_expr}'")
        for feature in features:
            feature.prune_by_flat_tags(user_expr)

    if user_feature_tag_expr != "":
        l.ttrace("filter tests by feature-level tags...")
        user_expr = cucumber_tag_expressions.TagExpressionParser.parse(user_feature_tag_expr)
        l.ttrace(f"user feature-level tag expression: '{user_expr}'")
        for feature in features:
            feature.prune_by_tag_level(user_expr, 'feature_level')

    if user_scenario_tag_expr != "":
        l.ttrace("filter tests by scenario-level tags...")
        user_expr = cucumber_tag_expressions.TagExpressionParser.parse(user_scenario_tag_expr)
        l.ttrace(f"user scenario-level tag expression: '{user_expr}'")
        for feature in features:
            feature.prune_by_tag_level(user_expr, 'scenario_level')

    if user_example_tag_expr != "":
        l.ttrace("filter tests by example-level tags...")
        user_expr = cucumber_tag_expressions.TagExpressionParser.parse(user_example_tag_expr)
        l.ttrace(f"user example-level tag expression: '{user_expr}'")
        for feature in features:
            feature.prune_by_tag_level(user_expr, 'example_level')

    result = []

    for feature in features:
        if len(feature.scenarios) > 0 or len(feature.scenario_outlines) > 0:
            result.append(feature)
        else:
            l.ttrace(f"feature {feature.name} is empty after pruning; skipping entirely...")
            summary['skipped_features'].append(feature)

    return result


def execute_feature(i, feature):
    l.ttrace(f"executing feature '{feature.name}'...")
    feature.execute_scenarios()
    return i, feature


@click.command()
@click.argument('command', type=click.Choice(['run', 'show-html']), nargs=1)
@click.option('--tags', 'user_flat_tag_expr', default="", show_default=True, help='Filter tests by tags using a tag expression.')
@click.option('--feature-tags', 'user_feature_tag_expr', default="", show_default=True, help='Filter tests by feature tags.')
@click.option('--scenario-tags', 'user_scenario_tag_expr', default="", show_default=True,
              help='Filter tests by scenario/scenario outline tags.')
@click.option('--example-tags', 'user_example_tag_expr', default="", show_default=True, help='Filter tests by tags of example tables.')
@click.option('--parallel', 'parallel', default=1, type=click.IntRange(1, 65535), show_default=True, help='Execute features in parallel.')
@click.option('--log-level', 'log_level',
              type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE', 'TTRACE'], case_sensitive=True),
              help='Set log level.')
@click.option('--failed-repeat-count', 'failed_repeat_count', default=0, show_default=True, help='Repeat tests N times upon failure.')
@click.option('--html-report/--no-html-report', 'html_report', default=False, help='Generate a HTML report.')
@click.option('--port', 'port', default=6789, show_default=True, help='show-html: Run HTML report server on this port.')
@click.argument('feature_paths', nargs=-1)
def click_parser(command, user_flat_tag_expr, user_feature_tag_expr, user_scenario_tag_expr, user_example_tag_expr, feature_paths, parallel,
                 log_level, failed_repeat_count, html_report, port):
    """Tasmanium - a simple BDD framework."""
    if command == 'run':
        run(user_flat_tag_expr, user_feature_tag_expr, user_scenario_tag_expr, user_example_tag_expr, feature_paths, parallel, log_level,
            failed_repeat_count, html_report)
    elif command == 'show-html':
        show_html(port)
    else:
        print(f"Unknown command '{command}'")
        exit()


def show_html(port: int):
    directory = "html_report"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving HTML report at http://localhost:{port}/report.html")
        httpd.serve_forever()


def run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="", feature_paths="", parallel=1,
        log_level='TTRACE', failed_repeat_count=0, html_report=False):
    """Run feature files."""
    os.makedirs(f'logs/scenarios', exist_ok=True)
    if log_level is not None:
        logger.set_verbosity(log_level)
    context: Context = Context()
    context.get_options().failed_repeat_count = failed_repeat_count
    l.ttrace(f"Resolving paths {feature_paths}...")
    if len(feature_paths) == 0:
        l.ttrace(f"No paths provided - resolving the entire 'features' directory.")
        feature_paths = ['.']
    file_paths = _glob_feature_files_in_paths(feature_paths)
    l.ttrace(f"Resolved paths: {file_paths}")
    context.files = file_paths

    register_steps()
    _register_environment()

    features: List[Feature] = []
    l.ttrace(f"parsing feature files...")
    for file_path in file_paths:
        l.ttrace(f"parsing '{file_path}'...")
        features.append(Feature(file_path, context))

    summary: Dict[AnyStr, Any] = {
        'passed_features': [],
        'failed_features': [],
        'skipped_features': [],
        'passed_scenario_outlines': [],
        'failed_scenario_outlines': [],
        'skipped_scenario_outlines': [],
        'passed_pure_scenarios': [],
        'failed_pure_scenarios': [],
        'skipped_pure_scenarios': [],
        'passed_scenarios': [],
        'failed_scenarios': [],
        'skipped_scenarios': [],
        'passed_steps': [],
        'failed_steps': [],
        'skipped_steps': [],
        'not_executed_steps': [],
        'exception_groups': [],
    }

    features = filter_by_tags(features, summary, user_flat_tag_expr, user_feature_tag_expr, user_scenario_tag_expr, user_example_tag_expr)

    l.ttrace("+--------------------------------------------------------------------------------------------------------------+")
    l.ttrace("|--------------------------------------------- ENTERING MEATSPACE ---------------------------------------------|")
    l.ttrace("+--------------------------------------------------------------------------------------------------------------+")

    l.ttrace(f"executing 'before_all'...")
    before_all.execute(context)

    l.ttrace(f"executing {len(features)} features...")
    # mp.set_start_method('spawn')

    for i, processed_feature in mp.Pool(parallel).starmap(execute_feature, zip([n for n in range(len(features))], features)):
        features[i] = processed_feature

    l.ttrace(f"executing 'after_all'...")
    after_all.execute(context)

    l.ttrace("+-------------------------------------------------------------------------------------------------------------+")
    l.ttrace("|--------------------------------------------- LEAVING MEATSPACE ---------------------------------------------|")
    l.ttrace("+-------------------------------------------------------------------------------------------------------------+")

    l.ttrace(f"gathering data for summary...")

    for feature in features:
        if len(feature.results['passed_scenarios']) + len(feature.results['passed_scenario_outlines']) == len(feature.scenarios) + len(
                feature.scenario_outlines):
            summary['passed_features'].append(feature)
        else:
            summary['failed_features'].append(feature)

        for key in ['passed', 'failed', 'skipped']:
            summary[f'{key}_scenarios'].extend(feature.results[f'{key}_scenarios'])
            for scenario_outline in feature.results[f'{key}_scenario_outlines']:
                summary[f'{key}_scenario_outlines'].append(scenario_outline)
                for key2 in ['passed', 'failed', 'skipped']:
                    summary[f'{key2}_scenarios'].extend(scenario_outline.results[f'{key2}_scenarios'])

    for key in ['passed', 'failed', 'skipped']:
        for scenario in summary[f'{key}_scenarios']:
            for key2 in ['passed', 'failed', 'not_executed']:
                summary[f'{key2}_steps'].extend(scenario.last_results()[f'{key2}_steps'])

    for feature in features:
        for key in ['passed', 'failed', 'skipped']:
            for scenario in feature.results[f'{key}_scenarios']:
                summary[f'{key}_pure_scenarios'].append(scenario)

    all_scenarios = summary['passed_scenarios'] + summary['failed_scenarios'] + summary['skipped_scenarios']
    exception_groups: Dict[AnyStr, Dict[AnyStr, List[Scenario]]] = {}

    for scenario in all_scenarios:
        if len(scenario.last_results()['failed_steps']) > 0:
            step = scenario.last_results()['failed_steps'][0]
            exception_name = step.last_results()['exception']['name']
            exception_arg = step.last_results()['exception']['args'][0]
            if exception_name not in exception_groups:
                exception_groups[exception_name] = {}
                exception_groups[exception_name][exception_arg] = [scenario]
            elif exception_arg not in exception_groups[exception_name]:
                exception_groups[exception_name][exception_arg] = [scenario]
            else:
                exception_groups[exception_name][exception_arg].append(scenario)

    summary['exception_groups'] = exception_groups

    if html_report:
        l.debug("generating HTML report...")
        generate_html_report(features, all_scenarios, exception_groups)
    else:
        l.ttrace("HTML report is turned off - not generating")

    l.info(f"Summary:")
    l.info(f"  Features: {len(summary['passed_features'])} passed, "
           f"{len(summary['failed_features'])} failed, "
           f"{len(summary['skipped_features'])} skipped")
    l.info(f"  Scenario outlines: {len(summary['passed_scenario_outlines'])} passed, "
           f"{len(summary['failed_scenario_outlines'])} failed, "
           f"{len(summary['skipped_scenario_outlines'])} skipped")
    l.info(f"  Pure scenarios: {len(summary['passed_pure_scenarios'])} passed, "
           f"{len(summary['failed_pure_scenarios'])} failed, "
           f"{len(summary['skipped_pure_scenarios'])} skipped")
    l.info(f"  Scenarios (incl. from outlines): {len(summary['passed_scenarios'])} passed, "
           f"{len(summary['failed_scenarios'])} failed, "
           f"{len(summary['skipped_scenarios'])} skipped")
    l.info(f"  Steps: {len(summary['passed_steps'])} passed, "
           f"{len(summary['failed_steps'])} failed, "
           f"{len(summary['not_executed_steps'])} not executed")

    return summary

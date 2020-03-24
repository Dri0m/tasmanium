import importlib
import json
import time
import traceback
from typing import AnyStr, Dict, Optional, List, Tuple, Callable, Set, Any
from uuid import uuid4

from parse import parse

from tasmanium import logger
from tasmanium.constants import STATUS_PASSED, STATUS_FAILED, STATUS_SKIPPED, STATUS_NOT_EXECUTED
from tasmanium.exceptions import KeywordError, StepNotFoundError, EmptyFeatureError
from tasmanium.gherkin.parser import Parser
from tasmanium.gherkin.pickles.compiler import compile
from tasmanium.registrars import step_registrar, before_feature, before_scenario, before_step, after_step, after_scenario, after_feature

l = logger.getLogger(__name__)


class Options:
    def __init__(self):
        self.failed_repeat_count: int = 0


class Context:

    def __init__(self):
        # global
        self.__files: Optional[List[AnyStr]] = None
        self.__options = Options()
        # feature
        self.__feature: Optional[Feature] = None
        self.__scenario: Optional[Scenario] = None
        self.__step: Optional[Step] = None
        # user data dict
        self.__data: Dict[Any, Any] = {}

    def get(self, key: Any) -> Optional[Any]:
        """
        Get data from the dict-based context datastore.
        Returns `None` if the key is not found.
        """
        return self.__data.get(key)

    def set(self, key: Any, value: Any):
        """
        Save data to the dict-based context datastore.
        """
        self.__data[key] = value

    def docstring_type(self) -> Optional[AnyStr]:
        """
        Returns the type of step docstring or `None` if not specified.
        """
        return self.__step.docstring['content_type']

    def docstring(self) -> Optional[AnyStr]:
        """
        Returns step docstring data.
        """
        return self.__step.docstring['content']

    def docstring_json(self) -> Optional[Dict]:
        """
        Returns step docstring data parsed from JSON as a python object.
        Returns `None` if the docstring type is not `json`.
        If docstring type is `json` but the docstring data are not valid JSON, an error is raised before any tests are executed.
        """
        return self.__step.docstring_json

    def table(self) -> Optional[List[Dict]]:
        """
        Returns step data table (or `None`) restructured as a list of dicts, where each dict represents one line of the data table.
        """
        return self.__step.data_table

    def attach_plaintext(self, data: AnyStr, filename: Optional[AnyStr] = None, description: Optional[AnyStr] = None):
        """
        Attach plaintext data to the step. Can be attached anytime during step execution. Attachment order is preserved.
        If no filename is provided, it will be generated.
        TODO: Attachment data are kept in memory at the moment, which is unnecessary and can consume a lot of memory.
        """
        self.__step.attach_plaintext(data=data, filename=filename, description=description)

    def attach_image(self, data: bytes, filename: AnyStr, description: Optional[AnyStr] = None):
        """
        Attach image data to the step. Can be attached anytime during step execution. Attachment order is preserved.
        TODO: Filename is mandatory because of image extension. But the image encoding could be detected.
        TODO: Attachment data are kept in memory at the moment, which is unnecessary and can consume a lot of memory.
        """
        self.__step.attach_image(data=data, filename=filename, description=description)

    def attach_video(self, path: AnyStr, description: Optional[AnyStr] = None):
        """
        TODO: Not implemented.
        Attach a video. Provide a path and it will be copied into the report. Will raise error if the file does not exist.
        """
        raise NotImplementedError("Not implemented yet.")

    def attach_data(self, data: bytes, filename: AnyStr, description: Optional[AnyStr] = None):
        """
        TODO: Not implemented.
        TODO: Will be probably treated as a binary file, so no text/image previews.
        TODO: Maybe provide an enum for common filetypes (archives etc.) and reuse this method for the text/image/video methods.
        Attach some generic data to the step.
        """
        raise NotImplementedError("Not implemented yet.")

    def attach_file(self, path: AnyStr, description: Optional[AnyStr] = None):
        """
        TODO: Not implemented.
        TODO: Attaching memory data and file may reuse the same underlying functionality.
        Attach some generic file. Provide a path and it will be copied into the report. Will raise error if the file does not exist.
        """
        raise NotImplementedError("Not implemented yet.")

    def get_options(self) -> Options:
        """
        TODO: Should not be public.
        Some user-provided args are passed to the executor through Context.
        """
        return self.__options

    def set_feature(self, feature):
        """
        TODO: Should not be public.
        Set current feature.
        """
        self.__feature = feature

    def set_scenario(self, scenario):
        """
        TODO: Should not be public.
        Set current scenario.
        """
        self.__scenario = scenario

    def set_step(self, step):
        """
        TODO: Should not be public.
        Set current step.
        """
        self.__step = step


class Attachment:
    def __init__(self, type: AnyStr, filename: AnyStr, data: bytes, description: Optional[AnyStr] = None):
        self.type: AnyStr = type
        self.filename: AnyStr = filename
        self.data: bytes = data
        self.description: Optional[AnyStr] = description


class Step:
    def __init__(self, raw_step, last_absolute_keyword: List[AnyStr], context_ref: Context):
        self.context_ref: Context = context_ref
        self.text: AnyStr = raw_step['text']
        self.raw_text: AnyStr = raw_step.get('raw_text')

        self.docstring: Dict = {
            "content_type": raw_step['arguments'][0].get('contentType') if len(raw_step['arguments']) > 0 else None,
            "content": raw_step['arguments'][0].get('content') if len(raw_step['arguments']) > 0 else None,
        }
        self.docstring_json: Optional[Dict] = None
        if self.docstring['content_type'] == 'json':
            self.docstring_json = json.loads(self.docstring['content'])

        self.is_from_outline: bool = self.raw_text is not None
        self.identifiers: List[str] = []

        data_table = self.__process_data_table(raw_step['arguments'])
        self.data_table: Optional[List[Dict]] = data_table[0]
        self.raw_data_table: Optional[List[Dict]] = data_table[1]

        self.keyword: AnyStr = self.__process_relative_keyword(raw_step['keyword'], last_absolute_keyword)
        self.corresponding_function, self.function_kwargs = self.__bind_corresponding_function()
        self.repeat_count: int = -1
        self.results: List[Dict[AnyStr, Any]] = []
        self.attachments: List[List[Attachment]] = []
        self.increment()

    def last_id(self) -> str:
        return self.identifiers[self.repeat_count]

    def last_results(self) -> Dict[AnyStr, Any]:
        return self.results[self.repeat_count]

    def last_attachments(self) -> List[Attachment]:
        return self.attachments[self.repeat_count]

    def increment(self) -> None:
        self.repeat_count += 1
        self.results.append({
            'status': None,
            'exception': None,
            'traceback': None,
            'execution_time_ns': None,
        })
        self.identifiers.append(_generate_id())
        self.attachments.append([])

    @classmethod
    def __process_relative_keyword(cls, current_keyword, last_absolute_keyword: List):
        """If current step uses 'And' keyword, replace with last absolute keyword"""
        if current_keyword == 'And':
            if len(last_absolute_keyword) == 0:
                raise KeywordError("Use of 'And' keyword without context.")
            return last_absolute_keyword[0]
        else:
            if len(last_absolute_keyword) == 0:
                last_absolute_keyword.append(current_keyword)
            else:
                last_absolute_keyword[0] = current_keyword
            return current_keyword

    @classmethod
    def __process_data_table(cls, raw_arguments: Dict) -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """Converts the gherkin table into a list of python dicts"""
        if len(raw_arguments) == 0:
            return None, None

        raw_arguments = raw_arguments[0]

        if raw_arguments.get('rows') is None:
            return None, None

        result: List[Dict] = []
        raw_result: List[Dict] = []

        table_header = []
        raw_table_header = []
        first = True
        for row in raw_arguments['rows']:
            if first:
                first = False
                for cell in row['cells']:
                    table_header.append(cell['value'])
                    raw_table_header.append(cell['value'])
            else:
                result_entry = {}
                raw_result_entry = {}
                for i in range(len(table_header)):
                    result_entry[table_header[i]] = row['cells'][i]['value']
                    raw_result_entry[table_header[i]] = row['cells'][i]['value']
                result.append(result_entry)
                raw_result.append(raw_result_entry)

        return result, raw_result

    def __bind_corresponding_function(self) -> Tuple[Callable, Dict]:
        """Try to match step's text with a function and parse arguments"""
        func_dict: Dict = step_registrar[self.keyword].all
        function = func_dict.get(self.text)
        args = {}
        if function is None:
            found = False
            for decorator_text, function in func_dict.items():
                r = parse(decorator_text, self.text)
                if r is not None:
                    found = True
                    args = r.named
                    l.ttrace(f"args parsed from '{self.text}' by '{decorator_text}': {args}")
                    break

            if not found:
                raise StepNotFoundError(f"Could not find any step definition for step '{self.keyword} {self.text}'.")
        else:
            l.ttrace(f"binding '{self.text}' to function '{function.__name__}'")

        return function, args

    def __update_context(self):
        l.ttrace("updating context step data...")
        self.context_ref.set_step(self)

    def execute_step(self):
        self.__update_context()
        l.ttrace(f"executing 'before_step'...")
        before_step.execute(self.context_ref, self)
        l.ttrace("attaching docstring and data table...")
        if self.docstring_json is not None:
            self.attach_plaintext(filename="docstring.json", description="step docstring parsed as JSON",
                                  data=json.dumps(self.docstring_json, indent=4, sort_keys=False))
        elif self.docstring['content'] is not None:
            self.attach_plaintext(filename="docstring.txt",
                                  description=f"""step docstring{" (unsupported type '" + self.docstring['content_type'] + "')" if self.docstring['content_type'] is not None else ''}""",
                                  data=self.docstring['content'])
        if self.data_table is not None:
            self.attach_plaintext(filename="data_table.json", description="data table parsed as JSON",
                                  data=json.dumps(self.data_table, indent=4, sort_keys=False))
        l.ttrace(f"executing step '{self.text}' aka function '{self.corresponding_function.__name__}' with args {self.function_kwargs}...")
        start = time.perf_counter_ns()
        try:
            self.corresponding_function(self.context_ref, **self.function_kwargs)
            self.last_results()['status'] = STATUS_PASSED
            self.last_results()['exception'] = None
        except Exception as e:
            l.error(
                f"step '{self.text}' aka function '{self.corresponding_function.__name__}' with args {self.function_kwargs} FAILED:",
                exc_info=e)
            self.last_results()['status'] = STATUS_FAILED
            self.last_results()['exception'] = {
                'name': type(e).__name__,
                'args': e.args,
                'exception': e,
                'execution_time_ns': None,
            }
            self.last_results()['traceback'] = traceback.format_exc()
        end = time.perf_counter_ns()
        self.last_results()['execution_time_ns'] = end - start
        l.ttrace(f"executing 'after_step'...")
        after_step.execute(self.context_ref, self)

    def attach_plaintext(self, data: AnyStr, description: Optional[AnyStr] = None, filename: Optional[AnyStr] = None):
        """Attach a plaintext file to this step that will then be available in generated reports."""
        if data is None:
            raise ValueError("Cannot attach None.")

        if filename is None:
            filename = f"{self.last_id()}-{len(self.last_attachments())}.txt"

        self.last_attachments().append(Attachment('plaintext', filename, bytes(data, encoding='utf-8'), description))

    def attach_image(self, filename: AnyStr, data: bytes, description: Optional[AnyStr] = None):
        """Attach an image file to this step that will then be available in generated reports."""
        if data is None:
            raise ValueError("Cannot attach None.")

        if filename is None:
            raise ValueError("Must provide filename for images (for now).")

        self.last_attachments().append(Attachment('image', filename, data, description))


class Scenario:
    def __init__(self, raw_pickle: Dict, context_ref: Context):
        self.context_ref: Context = context_ref
        self.feature_name: AnyStr = raw_pickle['feature_name']
        self.name: AnyStr = raw_pickle['name']
        self.raw_name: Optional[AnyStr] = raw_pickle.get('raw_name')
        self.language: AnyStr = raw_pickle['language']
        self.examples_name: Optional[AnyStr] = raw_pickle.get('examples_name')
        self.uri: AnyStr = raw_pickle['uri']

        self.is_from_outline: bool = self.raw_name is not None
        self.identifiers: List[str] = []

        if self.is_from_outline:
            self.line_in_file: AnyStr = raw_pickle['locations']['scenario_outline']['line']
        else:
            self.line_in_file: AnyStr = raw_pickle['locations']['scenario']['line']

        self.steps: List[Step] = self.__process_steps(raw_pickle['steps'])
        self.tags: Dict[AnyStr, List[AnyStr]] = self.__process_tags(raw_pickle['tags'])
        self.repeat_count: int = -1
        self.results: List[Dict[AnyStr, Any]] = []
        self.__increment()
        self.overall_result: Optional[AnyStr] = None

    def last_id(self) -> str:
        return self.identifiers[self.repeat_count]

    def last_results(self) -> Dict[AnyStr, Any]:
        return self.results[self.repeat_count]

    def __increment(self) -> None:
        self.repeat_count += 1
        self.results.append({
            'passed_steps': [],
            'failed_steps': [],
            'not_executed_steps': [],
            'execution_time_ns': None,
        })
        self.identifiers.append(_generate_id())

    @classmethod
    def __process_tags(cls, raw_tags: Dict) -> Dict[AnyStr, List[AnyStr]]:
        """Converts the raw tags into multiple lists, one for each tag level"""
        result: Dict[AnyStr, List[AnyStr]] = {}
        for k, v in raw_tags.items():
            result[k] = []
            for raw_tag in v:
                result[k].append(raw_tag['name'])
        return result

    def __update_context(self):
        l.ttrace("updating context scenario data...")
        self.context_ref.set_scenario(self)

    def __process_steps(self, raw_steps: Dict) -> List[Step]:
        result: List[Step] = []
        last_absolute_keyword = []
        for raw_step in raw_steps:
            result.append(Step(raw_step, last_absolute_keyword,
                               self.context_ref))  # HACK: pass AnyStr 'last_absolute_keyword' as List to make it accessible
        return result

    def execute_steps(self) -> None:
        self.__execute_steps()
        while self.overall_result == STATUS_FAILED and self.repeat_count < self.context_ref.get_options().failed_repeat_count:
            for step in self.steps:
                step.increment()
            self.__increment()
            self.__execute_steps()

    def __execute_steps(self) -> None:
        self.__update_context()
        l.ttrace(f"executing 'before_scenario'...")
        before_scenario.execute(self.context_ref, self)

        l.ttrace(f"setting log handler...")
        logger.set_scenario_handler(self.last_id())

        l.ttrace(f"executing steps of scenario '{self.name}'...")
        start = time.perf_counter_ns()

        for step in self.steps:
            step.execute_step()
            if step.results[step.repeat_count]['status'] == STATUS_FAILED:
                break
        l.ttrace(f"gathering steps results...")
        self.overall_result = STATUS_PASSED
        for step in self.steps:
            if step.results[step.repeat_count]['status'] == STATUS_PASSED:
                self.results[self.repeat_count]['passed_steps'].append(step)
            elif step.results[step.repeat_count]['status'] == STATUS_FAILED:
                self.results[self.repeat_count]['failed_steps'].append(step)
                self.overall_result = STATUS_FAILED
            elif step.results[step.repeat_count]['status'] is None:
                self.results[self.repeat_count]['not_executed_steps'].append(step)
                step.results[step.repeat_count]['status'] = STATUS_NOT_EXECUTED

        end = time.perf_counter_ns()
        self.results[self.repeat_count]['execution_time_ns'] = end - start

        l.ttrace(f"removing log handler...")
        logger.remove_scenario_handler()

        l.ttrace(f"executing 'after_scenario'...")
        after_scenario.execute(self.context_ref, self)


class ScenarioOutline:
    def __init__(self, raw_name: AnyStr, scenarios: List[Scenario]):
        self.raw_name: AnyStr = raw_name
        self.scenarios: List[Scenario] = scenarios
        self.identifier = _generate_id()
        self.results: Dict[AnyStr, Any] = {
            'passed_scenarios': [],
            'failed_scenarios': [],
            'skipped_scenarios': [],
            'execution_time_ns': None,
        }
        self.overall_result: Optional[AnyStr] = None

    def execute_scenarios(self):
        l.ttrace(f"executing scenarios of scenario outline '{self.raw_name}'...")
        start = time.perf_counter_ns()
        for scenario in self.scenarios:
            scenario.execute_steps()
            l.ttrace(f"gathering scenario results...")
            if len(scenario.results[scenario.repeat_count]['failed_steps']) == 0:
                self.results['passed_scenarios'].append(scenario)
            else:
                self.results['failed_scenarios'].append(scenario)
        end = time.perf_counter_ns()
        self.results['execution_time_ns'] = end - start
        if len(self.scenarios) == len(self.results['passed_scenarios']):
            self.overall_result = STATUS_PASSED
        else:
            self.overall_result = STATUS_FAILED


class Feature:
    def __init__(self, file_path, context_ref: Context):
        self.context_ref: Context = context_ref
        parsed = self.__parse_feature_file(file_path)
        self.scenarios: List[Scenario] = parsed[0]
        self.scenario_outlines: List[ScenarioOutline] = parsed[1]
        self.name: AnyStr = self.scenarios[0].feature_name if len(self.scenarios) > 0 else self.scenario_outlines[0].scenarios[
            0].feature_name
        self.uri: Optional[AnyStr] = None
        self.identifier = _generate_id()
        self.results: Dict[AnyStr, Any] = {
            'passed_scenarios': [],
            'failed_scenarios': [],
            'skipped_scenarios': [],
            'passed_scenario_outlines': [],
            'failed_scenario_outlines': [],
            'skipped_scenario_outlines': [],
            'execution_time_ns': None,
        }
        self.overall_result: Optional[AnyStr] = None

    def __parse_feature_file(self, path: AnyStr) -> Tuple[List[Scenario], List[ScenarioOutline]]:
        """Run gherkin parser on a file"""
        with open(path, "r") as f:
            data = f.read()

        gherkin_document = Parser().parse(data)
        pickles = compile(gherkin_document)

        if len(pickles) == 0:
            raise EmptyFeatureError("Empty feature is not allowed.")

        all_scenarios: List[Scenario] = []
        for pickle in pickles:
            self.uri = path
            pickle['uri'] = path
            # print(json.dumps(pickle, indent=2, sort_keys=False))
            all_scenarios.append(Scenario(pickle, self.context_ref))

        pure_scenarios: List[Scenario] = []
        clustered_scenarios: Dict[AnyStr, List[Scenario]] = {}

        for scenario in all_scenarios:
            if scenario.is_from_outline:
                if clustered_scenarios.get(f"[L{scenario.line_in_file}] {scenario.raw_name}") is None:
                    clustered_scenarios[f"[L{scenario.line_in_file}] {scenario.raw_name}"] = [scenario]
                else:
                    clustered_scenarios[f"[L{scenario.line_in_file}] {scenario.raw_name}"].append(scenario)
            else:
                pure_scenarios.append(scenario)

        scenario_outlines: List[ScenarioOutline] = []

        for raw_name, scenarios in clustered_scenarios.items():
            scenario_outlines.append(ScenarioOutline(raw_name, scenarios))

        l.ttrace(f"pure scenarios: {pure_scenarios}")
        l.ttrace(f"clustered scenarios: {clustered_scenarios}")
        l.ttrace(f"scenario outlines: {scenario_outlines}")

        return pure_scenarios, scenario_outlines

    def __update_context(self):
        l.ttrace("updating context feature data...")
        self.context_ref.set_feature(self)

    def prune_by_flat_tags(self, expr):
        """Flatten the tag levels into one and remove all steps that do not match with given expression"""
        l.ttrace(f"pruning '{self.name}'")
        pruned_scenarios: List[Scenario] = []
        for scenario in self.scenarios:
            if expr.evaluate(_flatten_tags(scenario.tags)):
                pruned_scenarios.append(scenario)
            else:
                l.ttrace(f"pruning scenario with tags {scenario.tags}")
                scenario.overall_result = STATUS_SKIPPED
                self.results['skipped_scenarios'].append(scenario)
        self.scenarios = pruned_scenarios

        pruned_scenario_outlines: List[ScenarioOutline] = []
        for scenario_outline in self.scenario_outlines:
            pruned_scenarios: List[Scenario] = []
            for scenario in scenario_outline.scenarios:
                if expr.evaluate(_flatten_tags(scenario.tags)):
                    pruned_scenarios.append(scenario)
                else:
                    l.ttrace(
                        f"pruning scenario '{scenario.name}' from examples table '{scenario.examples_name}' with"
                        f"tags {scenario.tags} in scenario outline '{scenario_outline.raw_name}'"
                    )
                    scenario.overall_result = STATUS_SKIPPED
                    scenario_outline.results['skipped_scenarios'].append(scenario)
            if len(scenario_outline.scenarios) == len(scenario_outline.results['skipped_scenarios']):
                self.results['skipped_scenario_outlines'].append(scenario_outline)
                scenario_outline.overall_result = STATUS_SKIPPED
            else:
                pruned_scenario_outlines.append(scenario_outline)
            scenario_outline.scenarios = pruned_scenarios

        self.scenario_outlines = pruned_scenario_outlines

        if len(self.scenarios) == 0 and len(self.scenario_outlines) == 0:
            self.overall_result = STATUS_SKIPPED

    def prune_by_tag_level(self, expr, level: AnyStr):
        """Remove all steps that do not match with given expression for a given tag level"""
        l.ttrace(f"pruning '{self.name}'")
        pruned_scenarios: List[Scenario] = []
        for scenario in self.scenarios:
            if expr.evaluate(scenario.tags[level]):
                pruned_scenarios.append(scenario)
            else:
                l.ttrace(f"pruning scenario with tags {scenario.tags}")
                self.results['skipped_scenarios'].append(scenario)
                self.results['skipped_pure_scenarios'].append(scenario)
        self.scenarios = pruned_scenarios

        for scenario_outline in self.scenario_outlines:
            pruned_scenarios: List[Scenario] = []
            for scenario in scenario_outline.scenarios:
                if expr.evaluate(scenario.tags[level]):
                    pruned_scenarios.append(scenario)
                else:
                    l.ttrace(
                        f"pruning scenario '{scenario.name}' from examples table '{scenario.examples_name}' with"
                        f"tags {scenario.tags} in scenario outline '{scenario_outline.raw_name}'"
                    )
                    scenario_outline.results['skipped_scenarios'].append(scenario)
            if len(scenario_outline.scenarios) == len(scenario_outline.results['skipped_scenarios']):
                self.results['skipped_scenario_outlines'].append(scenario_outline)
            scenario_outline.scenarios = pruned_scenarios

        if len(self.scenarios) == 0 and len(self.scenario_outlines) == 0:
            self.overall_result = STATUS_SKIPPED

    def execute_scenarios(self):
        _register_environment()  # register again because of parallelism
        self.__update_context()
        l.ttrace(f"executing 'before_feature'...")
        before_feature.execute(self.context_ref, self)

        start = time.perf_counter_ns()

        l.ttrace(f"executing scenarios of feature '{self.name}'...")
        for scenario in self.scenarios:
            l.ttrace(f"executing scenario '{scenario.name}'")
            scenario.execute_steps()

        l.ttrace(f"executing scenario outlines of feature '{self.name}'...")
        for scenario_outline in self.scenario_outlines:
            l.ttrace(f"executing scenario outline '{scenario_outline.raw_name}'")
            scenario_outline.execute_scenarios()

        end = time.perf_counter_ns()
        self.results['execution_time_ns'] = end - start

        l.ttrace(f"gathering results from scenarios...")
        for scenario in self.scenarios:
            if len(scenario.results[scenario.repeat_count]['failed_steps']) == 0:
                self.results['passed_scenarios'].append(scenario)
            else:
                self.results['failed_scenarios'].append(scenario)

        l.ttrace(f"gathering results from scenario outlines...")
        for scenario_outline in self.scenario_outlines:
            if len(scenario_outline.results['passed_scenarios']) == len(scenario_outline.scenarios):
                self.results['passed_scenario_outlines'].append(scenario_outline)
            else:
                self.results['failed_scenario_outlines'].append(scenario_outline)

        l.ttrace(f"updating overall status...")
        if len(self.scenarios) > 0 or len(self.scenario_outlines) > 0:
            if len(self.scenarios) == len(self.results['passed_scenarios']) and \
                    len(self.scenario_outlines) == len(self.results['passed_scenario_outlines']):
                self.overall_result = STATUS_PASSED
            else:
                self.overall_result = STATUS_FAILED

        l.ttrace(f"executing 'after_feature'...")
        after_feature.execute(self.context_ref, self)


def _flatten_tags(tags: Dict[AnyStr, List[AnyStr]]) -> List[AnyStr]:
    flat_tags: Set[AnyStr] = set()
    for tag_level in tags.values():
        flat_tags = flat_tags.union(set(tag_level))
    l.ttrace(f"tags: {flat_tags}")
    return list(flat_tags)


def _register_environment():
    """Import environment so that decorators on them run and the before/after functions are registered."""
    importlib.import_module('environment')


def _generate_id():
    return f"{uuid4().hex}{time.time_ns()}"

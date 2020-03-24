import os
from pathlib import Path
from shutil import copy2
from typing import List, Dict, AnyStr

from Cheetah.Template import Template

from tasmanium import logger
from tasmanium.boiled_pickle import Scenario, Feature

l = logger.getLogger(__name__)


def generate_html_report(features: List[Feature], scenarios: List[Scenario], exception_groups: Dict[AnyStr, Dict[AnyStr, List[Scenario]]]):
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/template/index.tmpl", "r") as f:
        file = f.read()
    os.makedirs('html_report', exist_ok=True)

    l.ttrace(f"generating html report...")
    data = {
        'features': features,
        'scenarios': scenarios,
        'exception_groups': exception_groups,
    }
    with open("html_report/report.html", "wb") as f:
        f.write(bytes(str(Template(file, searchList=[data])), encoding='utf-8'))

    l.ttrace(f"copying scenario logs...")
    for scenario in scenarios:
        for repeat in range(scenario.repeat_count + 1):
            os.makedirs(f'html_report/{scenario.identifiers[repeat]}/', exist_ok=True)
            path = f"logs/scenarios/{scenario.identifiers[repeat]}.log"
            if not Path(path).resolve().exists():
                continue
            l.ttrace(f"copying scenario log '{path}'...")
            copy2(path, f"html_report/{scenario.identifiers[repeat]}/scenario.log")

    l.ttrace(f"copying scenario attachments...")
    for scenario in scenarios:
        for repeat in range(scenario.repeat_count + 1):
            for step in scenario.steps:
                for attachment in step.attachments[repeat]:
                    l.ttrace(
                        f"copying attachment '{scenario.identifiers[repeat]}/{step.identifiers[repeat]}/{attachment.filename}'")
                    os.makedirs(f'html_report/{scenario.identifiers[repeat]}/{step.identifiers[repeat]}/', exist_ok=True)
                    with open(
                            f"html_report/{scenario.identifiers[repeat]}/{step.identifiers[repeat]}/{attachment.filename}",
                            "wb") as f:
                        f.write(attachment.data)

    for source_file in ['style.css', 'js.js']:
        copy2(f"{os.path.dirname(os.path.realpath(__file__))}/template/{source_file}", f"html_report/")

import os
import threading
import unittest
import warnings
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from tasmanium import logger
from tasmanium.boiled_pickle import Scenario, Step
from tasmanium.runner import run, show_html

# test list
flat_view_button_id = (By.ID, 'show-flat')
group_by_outlines_button_id = (By.ID, 'show-outlines')
group_by_features_button_id = (By.ID, 'show-features')
group_by_exceptions_button_id = (By.ID, 'show-exceptions')

test_list_id = (By.ID, 'test-list')
test_list_flat_id = (By.ID, 'test-list-flat')
test_list_outlines_id = (By.ID, 'test-list-outlines')
test_list_features_id = (By.ID, 'test-list-features')
test_list_exceptions_id = (By.ID, 'test-list-exceptions')

toggle_passed_button_id = (By.ID, 'toggle-passed')
toggle_failed_button_id = (By.ID, 'toggle-failed')
toggle_skipped_button_id = (By.ID, 'toggle-skipped')

test_list_button_text = lambda text: (By.XPATH, f"//button[contains(text(), '{text}')]")
test_list_first_level_entries = lambda list_id, status: (By.XPATH, f"//div[@id='{list_id}']/button[contains(@class, '{status}')]")
list_entry_id = lambda list_id, entry_id: (By.ID, f'entry-{list_id}-{entry_id}')

# single test content
single_test_content_div_by_id = lambda identifier: (By.ID, f'scenario-{identifier}')
scenario_header_by_id = lambda identifier: (By.ID, f'scenario-header-{identifier}')
exception_header_by_id = lambda identifier: (By.ID, f'exception-header-{identifier}')
exception_by_id = lambda identifier: (By.ID, f'exception-{identifier}')
footer_feature_uri_by_id = lambda identifier: (By.ID, f'footer-feature-uri-{identifier}')
footer_repeat_by_id = lambda identifier: (By.ID, f'footer-repeat-{identifier}')
footer_outline_name_by_id = lambda identifier: (By.ID, f'footer-outline-name-{identifier}')
footer_execution_time_by_id = lambda identifier: (By.ID, f'footer-execution-time-{identifier}')
step_by_id = lambda identifier: (By.ID, f'step-{identifier}')

step_span_text_by_id = lambda identifier: (By.ID, f'step-text-{identifier}')
step_attachment_count_by_id = lambda identifier: (By.ID, f'step-attachment-count-{identifier}')
step_execution_time_by_id = lambda identifier: (By.ID, f'step-execution-time-{identifier}')
step_attachments_by_id = lambda identifier: (By.XPATH, f"//div[@id='step-attachments-{identifier}']/div")
step_attachment_by_id_index = lambda identifier, index: (By.ID, f'step-attachment-{identifier}-{index}')
step_attachment_attribute_by_id_index = lambda identifier, index, attribute: (By.ID, f'step-attachment-{identifier}-{index}-{attribute}')

show_repeats_button_by_ids = lambda last_id, current_id: (By.ID, f"show-repeats-{last_id}-{current_id}")
test_repeat_button_by_ids = lambda last_id, current_id: (By.ID, f"test-repeat-button-{last_id}-{current_id}")

# scenario toolbar
toggle_steps_button_by_id = lambda identifier: (By.ID, f"toggle-steps-{identifier}")
show_scenario_log_button_by_id = lambda identifier: (By.ID, f"show-log-{identifier}")

# file modal
file_modal_content_div = (By.ID, "file-modal-content")
file_modal_contents_plaintext_div = (By.ID, "file-modal-contents-plaintext")
file_modal_close_span = (By.ID, "file-modal-close")

l = logger.getLogger(__name__)


class Browser:
    def __init__(self):
        self.driver = webdriver.Remote(command_executor='http://127.0.0.1:4444/wd/hub', desired_capabilities=DesiredCapabilities.CHROME)
        self.driver.set_window_position(0, 0)
        self.driver.set_window_size(1920, 1080)
        self.previous_element = None
        self.previous_element_style = None

    def wait_for_element(self, locator):
        l.trace(f"waiting for locator '{locator}'...")
        wait = WebDriverWait(self.driver, 2, poll_frequency=0.05)
        element = wait.until(ec.visibility_of_element_located(locator))
        if self.previous_element is not None:
            try:
                self.driver.execute_script("arguments[0].setAttribute('style','arguments[1]')", self.previous_element,
                                           self.previous_element_style)
            except StaleElementReferenceException:
                pass
        self.driver.execute_script("arguments[0].setAttribute('style','border: 2px solid red')", element)
        self.previous_element = element
        self.previous_element_style = element.get_attribute('style')
        return element


class HTMLReporter(unittest.TestCase):
    """Execute some tests and verify correct results in the HTML reporter."""

    browser = None
    HTML_REPORTER_PATH = f'http://127.0.0.1:6789/report.html'
    LOGS_PATH = f'{Path(os.getcwd()).parents[1]}/logs'
    original_dir = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.original_dir = os.getcwd()
        os.chdir(f'{Path(os.getcwd()).parents[1]}')
        warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
        cls.browser = Browser()

    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls.original_dir)
        # cls.browser.driver.quit()

    def assert_test_list_len(self, list_id, passed_count, failed_count, skipped_count):
        self.assertEqual(len(self.browser.driver.find_elements(*test_list_first_level_entries(list_id, 'passed'))), passed_count)
        self.assertEqual(len(self.browser.driver.find_elements(*test_list_first_level_entries(list_id, 'failed'))), failed_count)
        self.assertEqual(len(self.browser.driver.find_elements(*test_list_first_level_entries(list_id, 'skipped'))), skipped_count)

    def verify_test_view_header(self, scenario: Scenario, repeat: int):
        self.assertEqual(self.browser.wait_for_element(scenario_header_by_id(scenario.identifiers[repeat])).text.strip(), scenario.name)

        if len(scenario.results[repeat]['failed_steps']) > 0:
            step = scenario.results[repeat]['failed_steps'][0]
            exception_header = f"{step.results[repeat]['exception']['name']} - {step.results[repeat]['exception']['args']}"
            self.assertEqual(self.browser.wait_for_element(exception_header_by_id(scenario.identifiers[repeat])).text.strip(),
                             exception_header)
            exception_text = step.results[repeat]['traceback']
            self.assertEqual(self.browser.wait_for_element(exception_by_id(scenario.identifiers[repeat])).text.strip(),
                             exception_text.strip())

        text = f"Path: {scenario.uri}"
        self.assertEqual(self.browser.wait_for_element(footer_feature_uri_by_id(scenario.identifiers[repeat])).text.strip(), text)

        if scenario.repeat_count > 0:
            text = f"Repeat: {repeat} out of {scenario.repeat_count}"
            self.assertEqual(self.browser.wait_for_element(footer_repeat_by_id(scenario.identifiers[repeat])).text.strip(), text)
        if scenario.is_from_outline:
            text = f"Outline: {scenario.raw_name}, Examples: {scenario.examples_name}"
            self.assertEqual(self.browser.wait_for_element(footer_outline_name_by_id(scenario.identifiers[repeat])).text.strip(), text)
        if scenario.results[repeat]['execution_time_ns'] is not None:
            text = f"Execution time: {scenario.results[repeat]['execution_time_ns'] / 1000000000:.3f}s"
            self.assertEqual(self.browser.wait_for_element(footer_execution_time_by_id(scenario.identifiers[repeat])).text.strip(), text)

    def verify_test_view_step_list(self, scenario: Scenario, repeat: int):
        for step in scenario.steps:
            self.verify_test_view_step(step, repeat)

    def verify_test_view_step(self, step: Step, repeat: int):
        class_string = self.browser.wait_for_element(step_by_id(step.identifiers[repeat])).get_attribute("class")
        if step.results[repeat]['status'] is not None:
            status = step.results[repeat]['status'].replace('_', '-')
            self.assertTrue(status in class_string, f"'{status}' not found in '{class_string}'")
            self.assertTrue(
                str(len(step.last_attachments())) in self.browser.wait_for_element(
                    step_attachment_count_by_id(step.identifiers[repeat])).text)
            self.assertEqual(self.browser.wait_for_element(step_span_text_by_id(step.identifiers[repeat])).text.strip(),
                             f'{step.keyword} {step.text}')
            if step.results[repeat]['execution_time_ns'] is not None:
                text = f"{step.results[repeat]['execution_time_ns'] / 1000000000:.3f}s"
                self.assertEqual(self.browser.wait_for_element(step_execution_time_by_id(step.identifiers[repeat])).text.strip(), text)

            if len(step.last_attachments()) > 0:
                self.verify_step_attachments(step, repeat)

    def verify_step_attachments(self, step: Step, repeat: int):
        self.browser.wait_for_element(step_by_id(step.identifiers[repeat])).click()
        step_attachments = self.browser.driver.find_elements(*step_attachments_by_id(step.identifiers[repeat]))
        self.assertEqual(len(step_attachments), len(step.last_attachments()))

        for i in range(len(step.last_attachments())):
            attachment = step.last_attachments()[i]
            filename = self.browser.wait_for_element(step_attachment_attribute_by_id_index(step.identifiers[repeat], i, 'filename'))
            description = self.browser.wait_for_element(step_attachment_attribute_by_id_index(step.identifiers[repeat], i, 'description'))
            attachment_type = self.browser.wait_for_element(step_attachment_attribute_by_id_index(step.identifiers[repeat], i, 'type'))

            self.assertEqual(filename.text.strip(), attachment.filename)
            if attachment.description is not None:
                self.assertEqual(description.text.strip(), attachment.description)
            else:
                self.assertEqual(description.text.strip(), "No description available")
            self.assertEqual(attachment_type.text.strip(), attachment.type)
            # TODO verify attachment modal

    def verify_scenario_toolbar(self, scenario: Scenario, repeat: int):
        # expand all
        for step in scenario.steps:
            self.assertTrue('active' not in self.browser.wait_for_element(step_by_id(step.identifiers[repeat])).get_attribute('class'))
        self.browser.wait_for_element(toggle_steps_button_by_id(scenario.identifiers[repeat])).click()
        for step in scenario.steps:
            self.assertTrue('active' in self.browser.wait_for_element(step_by_id(step.identifiers[repeat])).get_attribute('class'))
        self.browser.wait_for_element(toggle_steps_button_by_id(scenario.identifiers[repeat])).click()
        for step in scenario.steps:
            self.assertTrue('active' not in self.browser.wait_for_element(step_by_id(step.identifiers[repeat])).get_attribute('class'))

        # view log
        if scenario.overall_result == 'skipped':
            self.assertFalse(self.browser.wait_for_element(show_scenario_log_button_by_id(scenario.identifiers[repeat])).is_enabled())
        else:
            self.browser.wait_for_element(show_scenario_log_button_by_id(scenario.identifiers[repeat])).click()
            self.browser.wait_for_element(file_modal_content_div)
            log_text = self.browser.wait_for_element(file_modal_contents_plaintext_div).text.strip()
            with open(f'{self.LOGS_PATH}/scenarios/{scenario.identifiers[repeat]}.log', 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    self.assertTrue(line in log_text)
            self.browser.wait_for_element(file_modal_close_span).click()

    def verify_scenario_view(self, scenario: Scenario):
        list_entry = self.browser.wait_for_element(list_entry_id('flat', scenario.last_id()))
        self.assertTrue(f"entry-{scenario.overall_result}" in list_entry.get_attribute("class"))
        self.assertEqual(list_entry.text.strip(), scenario.name)
        list_entry.click()

        if scenario.repeat_count == 0:
            self.assertFalse(self.browser.wait_for_element(show_repeats_button_by_ids(scenario.last_id(), scenario.last_id())).is_enabled())
            self.browser.wait_for_element(single_test_content_div_by_id(scenario.last_id()))
            self.verify_test_view_header(scenario, 0)
            self.verify_scenario_toolbar(scenario, 0)
            self.verify_test_view_step_list(scenario, 0)
        else:
            for repeat in range(scenario.repeat_count, -1, -1):
                self.browser.wait_for_element(single_test_content_div_by_id(scenario.identifiers[repeat]))
                self.verify_test_view_header(scenario, repeat)
                self.verify_scenario_toolbar(scenario, repeat)
                self.verify_test_view_step_list(scenario, repeat)
                if repeat > 0:
                    self.browser.wait_for_element(show_repeats_button_by_ids(scenario.last_id(), scenario.identifiers[repeat])).click()
                    self.browser.wait_for_element(test_repeat_button_by_ids(scenario.last_id(), scenario.identifiers[repeat - 1])).click()

    def verify_html_reporter(self, summary):
        threading.Thread(target=show_html, args=[6789], daemon=True).start()
        self.browser.driver.get(self.HTML_REPORTER_PATH)
        self.browser.wait_for_element(test_list_id)

        self.assertEqual(self.browser.wait_for_element(toggle_passed_button_id).text, 'Hide passed')
        self.assertEqual(self.browser.wait_for_element(toggle_failed_button_id).text, 'Hide failed')
        self.assertEqual(self.browser.wait_for_element(toggle_skipped_button_id).text, 'Hide skipped')

        # scenario grouping
        self.browser.wait_for_element(flat_view_button_id).click()
        self.assert_test_list_len(test_list_flat_id[1],
                                  passed_count=len(summary['passed_scenarios']),
                                  failed_count=len(summary['failed_scenarios']),
                                  skipped_count=len(summary['skipped_scenarios']))

        # scenario views
        self.browser.wait_for_element(flat_view_button_id).click()
        for scenario in summary['passed_scenarios'] + summary['failed_scenarios'] + summary['skipped_scenarios']:
            self.verify_scenario_view(scenario)

        # scenario outline grouping
        self.browser.wait_for_element(group_by_outlines_button_id).click()
        self.assert_test_list_len(test_list_outlines_id[1],
                                  passed_count=len(summary['passed_pure_scenarios']) + len(summary['passed_scenario_outlines']),
                                  failed_count=len(summary['failed_pure_scenarios']) + len(summary['failed_scenario_outlines']),
                                  skipped_count=len(summary['skipped_pure_scenarios']) + len(summary['skipped_scenario_outlines']))

        # feature grouping
        self.browser.wait_for_element(group_by_features_button_id).click()
        self.assert_test_list_len(test_list_features_id[1],
                                  passed_count=len(summary['passed_features']),
                                  failed_count=len(summary['failed_features']),
                                  skipped_count=len(summary['skipped_features']))

        # exception grouping
        self.browser.wait_for_element(group_by_exceptions_button_id).click()
        self.assert_test_list_len(test_list_exceptions_id[1],
                                  passed_count=0,
                                  failed_count=len(summary['exception_groups']),
                                  skipped_count=0)

    def test_simple_feature(self):
        feature_paths = [f'/tests/simple_feature.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_two_scenarios(self):
        feature_paths = [f'/tests/two_scenarios.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_simple_scenario_outline(self):
        feature_paths = [f'/tests/simple_scenario_outline.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_two_scenario_outlines(self):
        feature_paths = [f'/tests/two_scenario_outlines.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_simple_scenario_outline_more_examples(self):
        feature_paths = [f'/tests/simple_scenario_outline_more_examples.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_two_scenario_outlines_more_examples(self):
        feature_paths = [f'/tests/two_scenario_outlines_more_examples.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_simple_scenario_outline_more_tables(self):
        feature_paths = [f'/tests/simple_scenario_outline_more_tables.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_two_scenario_outlines_more_tables(self):
        feature_paths = [f'/tests/two_scenario_outlines_more_tables.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_simple_scenario_outline_more_examples_more_tables(self):
        feature_paths = [f'/tests/simple_scenario_outline_more_examples_more_tables.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_two_scenario_outlines_more_examples_more_tables(self):
        feature_paths = [f'/tests/two_scenario_outlines_more_examples_more_tables.feature']
        summary = run(user_flat_tag_expr="", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', html_report=True)
        self.verify_html_reporter(summary)

    def test_large_feature_with_everything(self):
        feature_paths = [f'/tests/large_feature_with_everything.feature']
        summary = run(user_flat_tag_expr="not @skipme", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', failed_repeat_count=2, html_report=True)

        for scenario in summary['failed_scenarios']:
            self.assertGreater(scenario.repeat_count, 0)
            for r in range(scenario.repeat_count):
                self.assertEqual(len(scenario.results[r]['failed_steps']), 1)

        self.verify_html_reporter(summary)


class Unit(unittest.TestCase):
    """Execute some tests and verify some tidbits."""

    original_dir = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.original_dir = os.getcwd()
        os.chdir(f'{Path(os.getcwd()).parents[1]}')

    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls.original_dir)

    def test_verify_repeat_data_are_stored(self):
        feature_paths = [f'/tests/large_feature_with_everything.feature']
        summary = run(user_flat_tag_expr="not @skipme", user_feature_tag_expr="", user_scenario_tag_expr="", user_example_tag_expr="",
                      feature_paths=feature_paths, parallel=1, log_level='TTRACE', failed_repeat_count=5)
        # TODO verify more stuff
        for scenario in summary['failed_scenarios']:
            self.assertGreater(scenario.repeat_count, 0)
            for r in range(scenario.repeat_count):
                self.assertEqual(len(scenario.results[r]['failed_steps']), 1)


if __name__ == '__main__':
    unittest.main(warnings='ignore')

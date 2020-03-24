from tasmanium import logger
from tasmanium.registrars import before_all, before_feature, before_scenario, before_step, after_step, after_scenario, \
    after_feature, after_all

l = logger.getLogger(__name__)


@before_all
def before_all_func(context):
    l.debug("hello from 'before_all'")


@before_feature
def before_feature_func(context, feature):
    l.debug("hello from 'before_feature'")


@before_scenario
def before_scenario_func(context, scenario):
    l.debug("hello from 'before_scenario'")


@before_step
def before_step_func(context, step):
    l.debug("hello from 'before_step'")


@after_step
def after_step_func(context, step):
    l.debug("hello from 'after_step'")


@after_scenario
def after_scenario_func(context, scenario):
    l.debug("hello from 'after_scenario'")


@after_feature
def after_feature_func(context, feature):
    l.debug("hello from 'after_feature'")


@after_all
def after_all_func(context):
    l.debug("hello from 'after_all'")

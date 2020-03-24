from typing import Callable, AnyStr

from tasmanium import logger
from tasmanium.exceptions import SingletonError

l = logger.getLogger(__name__)


def create_registrar():
    registry = {}

    def registrar_with_arg(text: AnyStr):
        def registrar(func: Callable):
            registry[text] = func
            return func

        return registrar

    registrar_with_arg.all = registry
    return registrar_with_arg


step_registrar = {}

Given = create_registrar()
When = create_registrar()
Then = create_registrar()

step_registrar['Given'] = Given
step_registrar['When'] = When
step_registrar['Then'] = Then


def singleton_registrar():
    function_ref = []

    def registrar(func: Callable):
        if len(function_ref) > 0:
            raise SingletonError("Cannot use singleton decorator twice.")
        l.ttrace(f"binding func '{func.__name__}' to a singleton registrar")
        function_ref.append(func)
        return func

    def execute(*args, **kwargs):
        if len(function_ref) == 0:
            l.ttrace("no function registered")
            return
        function_ref[0](*args, **kwargs)

    registrar.execute = execute
    return registrar


before_all = singleton_registrar()
before_feature = singleton_registrar()
before_scenario = singleton_registrar()
before_step = singleton_registrar()

after_step = singleton_registrar()
after_scenario = singleton_registrar()
after_feature = singleton_registrar()
after_all = singleton_registrar()

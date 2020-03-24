from tasmanium import logger
from tasmanium.registrars import Then

l = logger.getLogger(__name__)


@Then("he indeed exists")
def verify_user_exists(context):
    l.info("hello from the step 'Then he indeed exists'")

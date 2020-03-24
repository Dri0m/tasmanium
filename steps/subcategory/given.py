from tasmanium import logger
from tasmanium.registrars import Given

l = logger.getLogger(__name__)


@Given("a user which exists")
def create_user_that_exists(context):
    l.info(f"hello from the step 'Given a user which exists' - his data are {context.data_table} ")

    if context.data_table[0]['name'] == 'First B butterfly':
        context.attach_plaintext(data="A failing file in a failing test.")
        assert False, "assertion failed intentionally"

    context.attach_plaintext(filename="success.txt", data="this step succeeded!", description="Some description of this file.")
    context.attach_plaintext(filename="success2.txt", data="This step succeeded as well!")

    with open("D:/cool-crab.png", "rb") as f:
        context.step.attach_image(filename="cool-crab.png", data=f.read(), description="We can do pictures as well!")

    context.attach_plaintext(filename="success3.txt", data="Hi there! I am inside the file wee!",
                             description="Attach files anytime inside the step!")

    with open("D:/lipsum.txt", "r") as f:
        context.attach_plaintext(filename="lipsum.txt", data=f.read(), description="This is a long file, check it out.")

    # browser = webdriver.Remote(
    #     desired_capabilities=webdriver.DesiredCapabilities.FIREFOX,
    #     command_executor='http://localhost:4444/wd/hub'
    # )
    # from time import sleep
    # for _ in range(10):
    #     browser.get("https://www.seznam.cz")
    #     sleep(1)
    #     browser.get("https://www.google.com")
    #     sleep(1)
    #     browser.get("https://www.atlas.cz")
    #     sleep(1)
    #     browser.get("https://www.novinky.cz")
    #     sleep(1)
    #     browser.get("https://www.yahoo.com")


@Given("a user which {status}")
def create_user_doing_something(context, status):
    l.info(f"hello from the step 'Given a user which {{status}}' - i am '{status}' right now")
    l.info(f"my docstring type is {context.docstring_type}, my docstring is {context.docstring}")
    l.info(f"my docstring parsed as json is {context.docstring_json}")
    context.attach_plaintext(filename=f"success-status.txt", data=f"i am '{status}' right now")

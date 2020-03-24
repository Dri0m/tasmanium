from tasmanium import logger
from tasmanium.registrars import Given

l = logger.getLogger(__name__)


@Given("empty given")
def empty_given(context):
    pass


@Given("exemplar {value} given")
def exemplar_given(context, value):
    if 'file' in value:
        context.attach_plaintext(filename="named-file.txt", data="some data")
        context.attach_plaintext(filename="named-file-description.txt", data="some data", description="named file")
        context.attach_plaintext(data="some data")
        context.attach_plaintext(data="some data", description="file without explicit name")
        with open("tasmanium/tests/colors.png", "rb") as f:
            img = f.read()
        context.attach_image(filename="named-file.png", data=img)
        context.attach_image(filename="named-file-description.png", data=img, description="named file")
    if 'fail' in value:
        assert False, "failed intentionally"
    pass

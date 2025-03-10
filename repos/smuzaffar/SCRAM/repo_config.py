from cms_static import get_jenkins
from os.path import basename, dirname, abspath

# GH read/write token: Use default ~/.github-token-cmsbot
GH_TOKEN = "~/.github-token-cmsbot"
# GH readonly token: Use default ~/.github-token-readonly
GH_TOKEN_READONLY = "~/.github-token-readonly"
CONFIG_DIR = dirname(abspath(__file__))
# GH bot user: Use default cmsbot
CMSBUILD_USER = "cmsbot"
GH_REPO_ORGANIZATION = "smuzaffar"

GITHUB_WEBHOOK_TOKEN = "U2FsdGVkX1/yGRI4T5Xuk69SIVHNLg1fgE1+BU1eiRemkuUdkmqIZD0ICUVaEuO2"
REQUEST_PROCESSOR = "simple-cms-bot"
TRIGGER_PR_TESTS = []
VALID_WEB_HOOKS = ["issue_comment"]
WEBHOOK_PAYLOAD = True
JENKINS_SERVER = get_jenkins("cms-jenkins")

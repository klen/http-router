from http_router import Router


# Initialize the router
router = Router(trim_last_slash=True)


# Plain path
# ----------
@router.route('/simple')
def simple():
    return 'simple'


# Get a binded function and options by the given path
fn, opts = router('/simple')
print(fn, opts)
#
# >> <function simple>, {}
#
assert fn() == 'simple'

# The Router will raise a Router.NotFound for an unknown path
try:
    fn, opts = router('/unknown')
except router.NotFound as exc:
    print("%r" % exc)
    #
    # >> NotFound('/unknown', 'GET')
    #


# Multiple paths are supported as well
# ------------------------------------
@router.route('/', '/home')
def index():
    return 'index'


print(router('/'))
#
# >> <function index>, {}
#

print(router('/home'))
#
# >> <function index>, {}
#


# Bind HTTP Methods
# -----------------
@router.route('/only-post', methods=['POST'])
def only_post():
    return 'only-post'


# The Router will raise a Router.MethodNotAllowed for an unsupported method
try:
    print(router('/only-post', method='GET'))
except router.MethodNotAllowed as exc:
    print("%r" % exc)

    #
    # >> MethodNotAllowed('/only-post', 'GET')
    #

print(router('/only-post', method='POST'))
#
# >> <function only_post>, {}
#


# Regex Expressions are supported
# -------------------------------
@router.route('/regex(/opt)?')
def optional():
    return 'opt'


print(router('/regex', method='POST'))
#
# >> <function optional>, {}
#

print(router('/regex/opt', method='POST'))
#
# >> <function optional>, {}
#


# Dynamic routes are here
# -----------------------
@router.route('/order1/{id}')
def order1(id=None):
    return 'order-%s' % id


print(router('/order1/42'))
#
# >> <function order1>, {'id': '42'}
#


# Dynamic routes with regex
# -------------------------
@router.route(r'/order2/{ id:\d{3} }')
def order2(id=None):
    return 'order-%s' % id


print(router('/order2/100'))
#
# >> <function order2>, {'id': '100'}
#

try:
    print(router('/order2/03'))
except router.NotFound:
    pass

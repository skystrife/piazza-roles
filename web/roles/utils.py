import requests
import piazza_api


def piazza_from_cookie_dict(cookies):
    piazza_rpc = piazza_api.rpc.PiazzaRPC()

    # HACK: The serialization of a CookieJar to a dict in requests drops
    # all additional cookie information like the domain. This is a problem
    # if a request asks for a cookie to be updated and grabs the wrong
    # domain.
    #
    # Unfortunately, we can't just set the domain after the jar has been
    # created due to the way the jar itself is structure. So instead, we
    # iterate over the serialized dictionary, manually creating cookies and
    # setting additional parameters that were lost before adding them to
    # the jar, which should place them in the right part of the jar's
    # structure so they can be found for updating later.
    jar = requests.utils.cookiejar_from_dict({})
    for key, value in cookies.items():
        cookie = requests.cookies.create_cookie(
            key, value, domain='piazza.com', secure=True)
        jar.set_cookie(cookie)

    piazza_rpc.session.cookies = jar
    return piazza_api.Piazza(piazza_rpc)

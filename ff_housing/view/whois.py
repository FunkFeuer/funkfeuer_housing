from ff_housing import model, utils
from flask.views import View
from flask import Response

class WhoisView(View):
    def dispatch_request(self, ip=None):
        ip = model.IP.query.filter(model.IP.ip_address.like(ip+"/_%")).first()
        if not ip or not ip.server:
            return Response('Not Found', 404)
        s = ip.server
        resp = {
            'ip' :      ip,
            'rdns' :      ip.rdns,
            'server':   s.id,
            'admin_c':  s.admin_c.id,
            'name': s.admin_c,
            'email':    s.admin_c.email
        }
        dictabc = lambda kv: "%s: %s" % (kv[0], str(kv[1]))
        resp = '\n'.join(map(dictabc, resp.items()))
        return Response(resp, mimetype="text/plain")

    def register_view(app, url="/api/whois"):
        app.add_url_rule(url+'/<ip>', view_func=WhoisView.as_view('apps_api'), methods=['GET',])

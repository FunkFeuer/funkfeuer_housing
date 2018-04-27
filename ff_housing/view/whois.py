from ff_housing import model, utils
from flask.views import View
from flask import Response
import ipaddress

class WhoisView(View):
    def dispatch_request(self, ip=None):
        try:
            ipaddress.ip_address(ip)
        except:
            return Response('requested address not valid.', 406)

        addr = self.search_ip(ip)
        if not addr:
            addr = self.search_subnets(ip)

        if not addr or not addr.server:
            return Response('Not Found', 404)
        s = addr.server
        resp = {
            'ip' :      addr.ip,
            'routed_subnet' :      addr.routed_subnet,
            'server':   's'+str(s.id),
            'admin_c': s.admin_c,
            'email':    s.admin_c.email
        }
        dictabc = lambda kv: "%s: %s" % (kv[0], str(kv[1]))
        resp = '\n'.join(map(dictabc, resp.items()))
        return Response(resp, mimetype="text/plain")

    def search_ip(self, ip):
        return model.IP.query.filter(model.IP.ip_address.like(ip+"/_%")).first()

    def search_subnets(self, ip):
        for subnet in model.IP.query.filter(model.IP.routed_subnet != None):
            if ipaddress.ip_address(ip) in ipaddress.ip_network(subnet.routed_subnet):
                return subnet
        return None

    def register_view(app, url="/api/whois"):
        app.add_url_rule(url+'/<ip>', view_func=WhoisView.as_view('apps_api_whois'), methods=['GET',])

from ff_housing import model, utils
from flask.views import View
from flask import Response
import ipaddress
from datetime import datetime

class rdnsView(View):
    def dispatch_request(self, ip, prefix):
        entries = self.rdns("%s/%s" % (ip, prefix))
        return Response('\n'.join(entries), 200, mimetype="text/plain")

    def rdns(self, subnet):
        entries = ["; generated %s UTC" % datetime.utcnow() ]
        try:
            subnet = ipaddress.ip_network(subnet)
        except:
            entries.append('; error: requested subnet not valid, try 1.33.7.0/24 or c0ff:ee::/64')
            return entries

        if subnet.version == 4:
            splitlen = int((subnet.max_prefixlen-(subnet.prefixlen - (subnet.prefixlen%8)) )/8)
        else:
            splitlen = int((subnet.max_prefixlen-subnet.prefixlen)/4)

        # get IPs
        for addr in model.IP.query.filter(
                model.IP.active == True,
                model.IP.server_id != None,
                model.IP.rdns != None,
                model.IP.ip_address.like(self._subnet_sql_match(subnet))
            ).order_by(model.IP.id):
            if ipaddress.ip_interface(addr.ip_address) in subnet:
                entries.append(self._ptr_line(addr, splitlen))

        # get routed subnet rDNS entries
        for addr in model.Subnet_rDNS.query.join(model.IP).filter(
                model.IP.active == True,
                model.IP.server_id != None,
                model.IP.rdns != None,
                model.Subnet_rDNS.ip_address.like(self._subnet_sql_match(subnet))
            ).order_by(model.IP.id):
            if ipaddress.ip_interface(addr.ip_address) in subnet:
                entries.append(self._ptr_line(addr, splitlen))

        return entries


    def _ptr_line(self, addr, splitlen):
        return "%s\tPTR\t%s." % \
                ('.'.join(addr.ip.reverse_pointer.split('.')[:splitlen]),
                    addr.rdns )

    def _subnet_sql_match(self, subnet):
        if subnet.version == 6:
            return "%s:%%" % (':'.join(str(subnet[0]).rstrip(':').split(':')[:-1]))
        else:
            splitlen = int(subnet.prefixlen/8)
            return "%s.%%" % ('.'.join(str(subnet[0]).split('.')[:splitlen]))

    def register_view(app, url="/api/rdns"):
        app.add_url_rule(url+'/<ip>/<prefix>', view_func=rdnsView.as_view('apps_api_rdns'), methods=['GET',])

import requests
from ff_housing import app

from flask_security import current_user


def get_status(poweroutlet):
    try:
        response = requests.get('%s%s' % (app.config.get('POWER_API'), poweroutlet.endpoint),
                            auth=(
                                app.config.get('POWER_USER'),
                                app.config.get('POWER_PASS')
                                )
                            )
        status = response.json()
    except:
        return None
    if status['state'] == 'ON':
        status['powered'] = True
    else:
        status['powered'] = False
    return status

def set_power(poweroutlet, powered):
    if not poweroutlet.switchable:
        return False

    if poweroutlet.server and False:
        # if socket is asigned to a server, only the server admin is allowed to switch
        if poweroutlet.server.admin_c is not current_user:
            return False

    if powered == False:
        data = 'OFF'
    else:
        data =  'ON'
    print('turning %s %s' % (poweroutlet, data))
    try:
        response = requests.post('%s%s' % (app.config.get('POWER_API'), poweroutlet.endpoint),
                            data = str(data),
                            headers = {'Content-Type': 'text/plain'},
                            auth = (
                                app.config.get('POWER_USER'),
                                app.config.get('POWER_PASS')
                                ),
                            )
        if response.status_code != 200:
            print('http %d error %s' % (response.status_code, response.text) )
            return False
        status = response.text
    except:
        return False
    return status

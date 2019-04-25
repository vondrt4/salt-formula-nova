# -*- coding: utf-8 -*-
'''
Custom Nova state
'''
import logging
import collections
from functools import wraps
LOG = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if the nova module is in __salt__
    '''
    return 'novang'


def flavor_present(name, flavor_id=0, ram=0, disk=0, vcpus=1, profile=None):
    '''
    Ensures that the nova flavor exists
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Flavor "{0}" already exists'.format(name)}
    project = __salt__['novang.flavor_list'](profile)
    if 'Error' in project:
        pass
    elif name in project:
        pass
    else:
        __salt__['novang.flavor_create'](name, flavor_id, ram, disk, vcpus, profile)
        ret['comment'] = 'Flavor {0} has been created'.format(name)
        ret['changes']['Flavor'] = 'Created'
    return ret


def map_instances(name='cell1'):
    '''
    Ensures that the nova instances are mapped to cell
    '''
    ret = {'name': name,
           'changes': {},
           'result': False,
           'comment': 'Cell "{0}" does not exists'.format(name)}
    cell_uuid = __salt__['cmd.shell']('nova-manage cell_v2 list_cells 2>&- | grep ' + name + ' | tr -d \"\n\" | awk \'{print $4}\'')
    if cell_uuid:
        try:
            __salt__['cmd.shell']('nova-manage cell_v2 map_instances --cell_uuid ' + cell_uuid)
            ret['result'] = True
            ret['comment'] = 'Instances were mapped to cell named {0}'.format(name)
            ret['changes']['Instances'] = 'Mapped to cell named {0}'.format(name)
        except:
            ret['result'] = False
            ret['comment'] = 'Error while mapping instances to cell named {0}'.format(name)
            ret['changes']['Instances'] = 'Failed to map to cell named {0}'.format(name)
    return ret


def api_db_version_present(name=None, version="20"):
    '''
    Ensures that specific api_db version is present
    '''
    ret = {'name': 'api_db --version',
           'changes': {},
           'result': True,
           'comment': 'Current Api_db version is not < than "{0}".'.format(version)}
    api_db_version = __salt__['cmd.shell']('nova-manage api_db version 2>/dev/null')
    try:
        api_db_version = int(api_db_version)
        version = int(version)
    except:
        # nova is not installed
        ret = _no_change('api_db --version', None, test=True)
        return ret
    if api_db_version < version:
        try:
            __salt__['cmd.shell']('nova-manage api_db sync --version ' + str(version))
            ret['result'] = True
            ret['comment'] = 'Nova-manage api_db sync --version {0} was successfuly executed'.format(version)
            ret['changes']['api_db'] = 'api_db sync --version {0}'.format(version)
        except:
            ret['result'] = False
            ret['comment'] = 'Error while executing nova-manage api_db sync --version {0}'.format(version)
            ret['changes']['api_db'] = 'Failed to execute api_db sync --version {0}'.format(version)
    return ret


def db_version_present(name=None, version="334"):
    '''
    Ensures that specific api_db version is present
    '''
    ret = {'name': 'db --version',
           'changes': {},
           'result': True,
           'comment': 'Current db version is not < than "{0}".'.format(version)}
    db_version = __salt__['cmd.shell']('nova-manage db version 2>/dev/null')
    try:
        db_version = int(db_version)
        version = int(version)
    except:
        # nova is not installed
        ret = _no_change('db --version', None, test=True)
        return ret

    if db_version < version:
        try:
            __salt__['cmd.shell']('nova-manage db sync --version ' + str(version))
            ret['result'] = True
            ret['comment'] = 'Nova-manage db sync --version {0} was successfuly executed'.format(version)
            ret['changes']['db'] = 'db sync --version {0}'.format(version)
        except:
            ret['result'] = False
            ret['comment'] = 'Error while executing nova-manage db sync --version {0}'.format(version)
            ret['changes']['db'] = 'Failed to execute db sync --version {0}'.format(version)
    return ret

def online_data_migrations_present(name=None, api_db_version="20", db_version="334"):
    '''
    Ensures that online_data_migrations are enforced if specific version of api_db and db is present
    '''
    ret = {'name': 'online_data_migrations',
           'changes': {},
           'result': True,
           'comment': 'Current api_db version != {0} a db version != {1}.'.format(api_db_version, db_version)}
    cur_api_db_version = __salt__['cmd.shell']('nova-manage api_db version 2>/dev/null')
    cur_db_version = __salt__['cmd.shell']('nova-manage db version 2>/dev/null')
    try:
        cur_api_db_version = int(cur_api_db_version)
        cur_db_version = int(cur_db_version)
        api_db_version = int(api_db_version)
        db_version = int(db_version)
    except:
        # nova is not installed
        ret = _no_change('online_data_migrations', None, test=True)
        return ret
    if cur_api_db_version == api_db_version and cur_db_version == db_version:
        try:
            __salt__['cmd.shell']('nova-manage db online_data_migrations')
            ret['result'] = True
            ret['comment'] = 'nova-manage db online_data_migrations was successfuly executed'
            ret['changes']['online_data_migrations'] = 'online_data_migrations on api_db version {0} and db version {1}'.format(api_db_version, db_version)
        except:
            ret['result'] = False
            ret['comment'] = 'Error while executing nova-manage db online_data_migrations'
            ret['changes']['online_data_migrations'] = 'Failed to execute online_data_migrations on api_db version {0} and db version {1}'.format(api_db_version, db_version)
    return ret

def quota_present(tenant_name, profile, name=None, **kwargs):
    '''
    Ensures that the nova quota exists
    '''
    changes = {}
    for key, value in kwargs.items():
        quota = __salt__['novang.quota_get'](key, tenant_name, profile)
        if quota != value:
            arg = {}
            arg[key] = value
            changes[key] = value
            __salt__['novang.quota_update'](tenant_name, profile, **arg)
    if bool(changes):
        return _updated(tenant_name, 'tenant', changes)
    else:
        return _no_change(tenant_name, 'tenant')


def availability_zone_present(name=None, availability_zone=None, profile=None):
    '''
    Ensures that the nova availability zone exists
    '''
    name = availability_zone
    zone_exists = __salt__['novang.availability_zone_get'](name, profile)
    if zone_exists == False:
        item_created = __salt__['novang.availability_zone_create'](name, availability_zone, profile)
        if bool(item_created):
            return _created(availability_zone, 'availabilty zone', item_created)         
    else:
        return _already_exists(availability_zone, 'availabilty zone')
    return existing_availability_zones

def aggregate_present(name=None, aggregate=None, profile=None):
    '''
    Ensures that the nova aggregate exists
    '''
    name = aggregate
    aggregate_exists = __salt__['novang.aggregate_get'](name, profile)
    if aggregate_exists == False:
        item_created = __salt__['novang.aggregate_create'](name, aggregate, profile)
        if bool(item_created):
            return _created(aggregate, 'aggregate', item_created)
    else:
        return _already_exists(aggregate, 'aggregate')
    return existing_aggregate


def instance_present(name, flavor, image, networks, security_groups=None, profile=None, tenant_name=None):
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Instance "{0}" already exists'.format(name)}
    kwargs = {}
    nics = []
    existing_instances = __salt__['novang.server_list'](profile, tenant_name)
    if name in existing_instances:
        return ret
    existing_flavors = __salt__['novang.flavor_list'](profile)
    if flavor in existing_flavors:
        flavor_id = existing_flavors[flavor]['id']
    else:
        return {'name': name,
                'changes': {},
                'result': False,
                'comment': 'Flavor "{0}" doesn\'t exists'.format(flavor)}

    existing_image = __salt__['novang.image_list'](image, profile)
    if not existing_image:
        return {'name': name,
                'changes': {},
                'result': False,
                'comment': 'Image "{0}" doesn\'t exists'.format(image)}
    else:
        image_id = existing_image.get(image).get('id')
    if security_groups is not None:
        kwargs['security_groups'] = []
        for secgroup in security_groups:
            existing_secgroups = __salt__['novang.secgroup_list'](profile, tenant_name)
            if not secgroup in existing_secgroups:
                return {'name': name,
                        'changes': {},
                        'result': False,
                        'comment': 'Security group "{0}" doesn\'t exists'.format(secgroup)}
            else:
                kwargs['security_groups'].append(secgroup)
    for net in networks:
        existing_network = __salt__['novang.network_show'](net.get('name'), profile)
        if not existing_network:
            return {'name': name,
                    'changes': {},
                    'result': False,
                    'comment': 'Network "{0}" doesn\'t exists'.format(net.get(name))}
        else:
            network_id = existing_network.get('id')
            if net.get('v4_fixed_ip') is not None:
                nics.append({'net-id': network_id, 'v4-fixed-ip': net.get('v4_fixed_ip')})
            else:
                nics.append({'net-id': network_id})
    kwargs['nics'] = nics
    new_instance_id = __salt__['novang.boot'] (name, flavor_id, image_id, profile, tenant_name, **kwargs)
    return {'name': name,
            'changes': {},
            'result': True,
            'comment': 'Instance "{0}" was successfuly created'.format(name)}


def keypair_present(name, pub_file, profile=None):
    """
    Ensures that the Nova key-pair exists
    """

    existing_keypairs = __salt__['novang.keypair_list'](profile)
    if name in existing_keypairs:
        return _already_exists(name, 'Keypair')
    else:
        res = __salt__['novang.keypair_add'](name, pubfile=pub_file,
                                             profile=profile)
        if res and res['name'] == name:
            return _created(name, 'Keypair', res)
        return _create_failed(name, 'Keypair')


def _already_exists(name, resource):
    changes_dict = {'name': name,
                    'changes': {},
                    'result': True}
    changes_dict['comment'] = \
        '{0} {1} already exists'.format(resource, name)
    return changes_dict


def _created(name, resource, resource_definition):
    changes_dict = {'name': name,
                    'changes': resource_definition,
                    'result': True,
                    'comment': '{0} {1} created'.format(resource, name)}
    return changes_dict

def _updated(name, resource, resource_definition):
    changes_dict = {'name': name,
                    'changes': resource_definition,
                    'result': True,
                    'comment': '{0} {1} tenant was updated'.format(resource, name)}
    return changes_dict

def _update_failed(name, resource):
    changes_dict = {'name': name,
                    'changes': {},
                    'comment': '{0} {1} failed to update'.format(resource, name),
                    'result': False}
    return changes_dict

def _no_change(name, resource, test=False):
    changes_dict = {'name': name,
                    'changes': {},
                    'result': True}
    if test:
        changes_dict['comment'] = \
            '{0} {1} will be {2}'.format(resource, name, test)
    else:
        changes_dict['comment'] = \
            '{0} {1} is in correct state'.format(resource, name)
    return changes_dict


def _create_failed(name, resource):
    changes_dict = {'name': name,
                    'changes': {},
                    'comment': '{0} {1} failed to create'.format(resource,
                                                                 name),
                    'result': False}
    return changes_dict

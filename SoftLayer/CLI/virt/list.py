"""List virtual servers."""
# :license: MIT, see LICENSE for more details.

import click

import SoftLayer
from SoftLayer.CLI import columns as column_helper
from SoftLayer.CLI.command import SLCommand as SLCommand
from SoftLayer.CLI import environment
from SoftLayer.CLI import formatting
from SoftLayer.CLI import helpers
from SoftLayer import utils

# pylint: disable=unnecessary-lambda

COLUMNS = [
    column_helper.Column('guid', ('globalIdentifier',)),
    column_helper.Column('primary_ip', ('primaryIpAddress',)),
    column_helper.Column('backend_ip', ('primaryBackendIpAddress',)),
    column_helper.Column('datacenter', ('datacenter', 'name')),
    column_helper.Column('action', lambda guest: formatting.active_txn(guest),
                         mask='''
                         activeTransaction[
                            id,transactionStatus[name,friendlyName]
                         ]'''),
    column_helper.Column('power_state', ('powerState', 'name')),
    column_helper.Column(
        'created_by',
        ('billingItem', 'orderItem', 'order', 'userRecord', 'username')),
    column_helper.Column(
        'tags',
        lambda server: formatting.tags(server.get('tagReferences')),
        mask="tagReferences.tag.name"),
]

DEFAULT_COLUMNS = [
    'id',
    'hostname',
    'primary_ip',
    'backend_ip',
    'datacenter',
    'action',
]


@click.command(cls=SLCommand, short_help="List virtual servers.")
@click.option('--cpu', '-c', help='Number of CPU cores', type=click.INT)
@click.option('--domain', '-D', help='Domain portion of the FQDN')
@click.option('--datacenter', '-d', help='Datacenter shortname')
@click.option('--hostname', '-H', help='Host portion of the FQDN')
@click.option('--memory', '-m', help='Memory in mebibytes', type=click.INT)
@click.option('--network', '-n', help='Network port speed in Mbps')
@click.option('--hourly', is_flag=True, help='Show only hourly instances')
@click.option('--monthly', is_flag=True, help='Show only monthly instances')
@click.option('--transient', help='Filter by transient instances', type=click.BOOL)
@click.option('--hardware', is_flag=True, default=False, help='Show the all VSI related to hardware')
@click.option('--all-guests', is_flag=True, default=False, help='Show the all VSI and hardware VSIs')
@helpers.multi_option('--tag', help='Filter by tags')
@click.option('--sortby',
              help='Column to sort by',
              default='hostname',
              show_default=True)
@click.option('--columns',
              callback=column_helper.get_formatter(COLUMNS),
              help='Columns to display. [options: %s]'
              % ', '.join(column.name for column in COLUMNS),
              default=','.join(DEFAULT_COLUMNS),
              show_default=True)
@click.option('--limit', '-l',
              help='How many results to get in one api call, default is 100',
              default=100,
              show_default=True)
@environment.pass_env
def cli(env, sortby, cpu, domain, datacenter, hostname, memory, network,
        hourly, monthly, tag, columns, limit, transient, hardware, all_guests):
    """List virtual servers."""

    vsi = SoftLayer.VSManager(env.client)
    guests = vsi.list_instances(hourly=hourly,
                                monthly=monthly,
                                hostname=hostname,
                                domain=domain,
                                cpus=cpu,
                                memory=memory,
                                datacenter=datacenter,
                                nic_speed=network,
                                transient=transient,
                                tags=tag,
                                mask=columns.mask(),
                                limit=limit)

    table = formatting.Table(columns.columns)
    table.sortby = sortby
    if not hardware or all_guests:
        for guest in guests:
            table.add_row([value or formatting.blank()
                           for value in columns.row(guest)])

        env.fout(table)

    if hardware or all_guests:
        hardware_guests = vsi.get_hardware_guests()
        for hd_guest in hardware_guests:
            if hd_guest['virtualHost']['guests']:
                title = "Hardware(id = {hardwareId}) guests associated".format(hardwareId=hd_guest['id'])
                table_hardware_guest = formatting.Table(['id', 'hostname', 'CPU', 'Memory', 'Start Date', 'Status',
                                                         'powerState'], title=title)
                table_hardware_guest.sortby = 'hostname'
                for guest in hd_guest['virtualHost']['guests']:
                    table_hardware_guest.add_row([
                        guest['id'],
                        guest['hostname'],
                        '%i %s' % (guest['maxCpu'], guest['maxCpuUnits']),
                        guest['maxMemory'],
                        utils.clean_time(guest['createDate']),
                        guest['status']['keyName'],
                        guest['powerState']['keyName']
                    ])
                env.fout(table_hardware_guest)

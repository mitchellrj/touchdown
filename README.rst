=========
Touchdown
=========

.. image:: https://travis-ci.org/yaybu/touchdown.png?branch=master
   :target: https://travis-ci.org/#!/yaybu/touchdown

.. image:: https://coveralls.io/repos/yaybu/touchdown/badge.png?branch=master
    :target: https://coveralls.io/r/yaybu/touchdown

.. image:: https://pypip.in/version/touchdown/badge.png
    :target: https://pypi.python.org/pypi/touchdown/


Touchdown is a service orchestration framework for python.

You can find us in #yaybu on irc.oftc.net.


Examples
========

Here is an example ``Touchdownfile``::

    from touchdown.core.renderable import Format, Json, Property

    aws = workspace.add_aws(
        region='eu-west-1',
    )

    vpc = aws.add_virtual_private_cloud(name='example')
    vpc.add_internet_gateway(name="internet")

    database = aws.add_database(
        name='database',
    )

    example = vpc.add_subnet(
        name='application',
        cidr_block='192.168.0.1/24',
    )

    asg = aws.add_autoscaling_group(
        name='example',
        launch_configuration=aws.add_launch_configuration(
            name="example",
            ami='ami-62366',
            subnets=[example],
            user_data=Json({
                "SECRET_KEY": "059849utiruoierutiou45",
                "DATABASES":
                    "default": {
                        "HOST": Property(database, "url"),
                    }, 
                },
            })
        ),
    )

You can then apply this configuration with::

    touchdown apply
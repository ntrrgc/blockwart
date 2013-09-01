.. _item_directory:

###############
Directory items
###############

.. code-block:: python

    directories = {
        "/path/to/directory": {
            "mode": "0644",
            "owner": "root",
            "group": "root",
        },
    }

Attribute reference
-------------------

``group``
+++++++++

Name of the group this directory belongs to.

``mode``
++++++++

Directory mode as returned by ``stat -c %a <directory>``.

``owner``
+++++++++

Username of the directory's owner.
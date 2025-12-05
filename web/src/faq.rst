==========================
Frequently Asked Questions
==========================

How do I modify system files directly?
--------------------------------------

Direct modification of immutable directories is not possible. You can make changes to your system by editing the :doc:`Systemfile <systemfile-reference>`, deploying the changes with ``os upgrade`` and then rebooting to the newly deployed system.

If you really must modify the current deployment, you can use ``os unlock``, but this should be used sparingly, and any changes reimplemented in the :doc:`Systemfile <systemfile-reference>` for the next deployment.

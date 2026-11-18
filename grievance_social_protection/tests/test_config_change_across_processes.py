"""
A process reloads the grievance configuration when the stored row differs
from the one it loaded, at its next access check after
CONFIG_CHECK_INTERVAL_SECONDS: a configuration saved by another process
(another web worker, a task worker) takes effect without a restart. Within
the interval an access check reads nothing from the database.

The other process is simulated by writing the row without the reloader that
ModuleConfiguration.save runs in the saving process only.
"""
import json
from unittest import mock

from django.apps import apps
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import ModuleConfiguration
from grievance_social_protection import apps as grievance_apps
from grievance_social_protection.access_control import GrievanceAccessControl
from grievance_social_protection.apps import TicketConfig
from grievance_social_protection.tests.test_config_reload_rights import MODULE, ReloadRightsTestBase

LOADED = {
    'grievance_types': ['general'],
    'grievance_flags': ['public'],
}
# Saved by the other process: 'general' restricted, a restricted flag 'secret'.
SAVED_ELSEWHERE = {
    'grievance_types': [{'name': 'general', 'permissions': ['read']}],
    'grievance_flags': ['public', {'name': 'secret', 'permissions': ['read']}],
}


class ConfigChangeAcrossProcessesTest(ReloadRightsTestBase):

    def setUp(self):
        super().setUp()
        for attribute in ('_config_checked_at', 'loaded_config_text'):
            patcher = mock.patch.object(TicketConfig, attribute, None)
            patcher.start()
            self.addCleanup(patcher.stop)
        ModuleConfiguration.objects.filter(module=MODULE, layer='be').delete()
        self.row = ModuleConfiguration.objects.create(
            module=MODULE, layer='be', version='1', config=json.dumps(LOADED))
        # This process loaded LOADED from the row.
        apps.get_app_config(MODULE)._reload_module_config(self.row)
        self.general = self._ticket('general')
        self.secret = self._ticket('general', 'secret')
        self.clock = mock.patch.object(grievance_apps.time, 'monotonic', return_value=1000.0)
        self.monotonic = self.clock.start()
        self.addCleanup(self.clock.stop)
        TicketConfig.reload_if_changed()

    def _saved_by_another_process(self, cfg):
        ModuleConfiguration.objects.filter(id=self.row.id).update(config=json.dumps(cfg))

    def _after(self, seconds):
        self.monotonic.return_value = 1000.0 + seconds

    def test_a_configuration_saved_elsewhere_is_enforced_after_the_interval(self):
        self.assertTrue(GrievanceAccessControl.check_category_access(self.user_without_vbg, 'general'))
        self.assertIn(self.secret.id, self._visible_ids(self.user_without_vbg))

        self._saved_by_another_process(SAVED_ELSEWHERE)
        self._after(grievance_apps.CONFIG_CHECK_INTERVAL_SECONDS)

        self.assertFalse(GrievanceAccessControl.check_category_access(self.user_without_vbg, 'general'))
        self.assertFalse(GrievanceAccessControl.check_flag_access(self.user_without_vbg, 'secret'))
        self.assertNotIn(self.secret.id, self._visible_ids(self.user_without_vbg))
        self.assertNotIn(self.general.id, self._visible_ids(self.user_without_vbg))

    def test_a_check_within_the_interval_reads_nothing(self):
        self._saved_by_another_process(SAVED_ELSEWHERE)
        self._after(grievance_apps.CONFIG_CHECK_INTERVAL_SECONDS / 2)
        with CaptureQueriesContext(connection) as queries:
            GrievanceAccessControl.check_category_access(self.user_without_vbg, 'general')
            TicketConfig.reload_if_changed()
        self.assertEqual(len(queries), 0)

    def test_an_unchanged_row_is_not_reloaded(self):
        self._after(grievance_apps.CONFIG_CHECK_INTERVAL_SECONDS)
        with mock.patch.object(grievance_apps.TicketConfig, '_reload_module_config') as reload:
            TicketConfig.reload_if_changed()
        reload.assert_not_called()

    def test_a_deleted_row_brings_the_default_configuration_back(self):
        ModuleConfiguration.objects.filter(id=self.row.id).delete()
        self._after(grievance_apps.CONFIG_CHECK_INTERVAL_SECONDS)
        TicketConfig.reload_if_changed()
        self.assertEqual(TicketConfig.grievance_flags, grievance_apps.DEFAULT_CFG['grievance_flags'])

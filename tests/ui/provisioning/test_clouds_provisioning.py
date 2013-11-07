# -*- coding: utf-8 -*-
# pylint: disa
import pytest
from fixtures.server_roles import default_roles, server_roles
from unittestzero import Assert
from tests.ui.provisioning.test_base_provisioning import TestBaseProvisioning


@pytest.mark.nondestructive
@pytest.mark.fixtureconf(server_roles=default_roles+('automate',))
@pytest.mark.usefixtures(
    "maximized",
    "setup_cloud_providers",
    "mgmt_sys_api_clients",
    "db_session",
    "soap_client")


class TestImageProvisioning(TestBaseProvisioning):
    def test_ec2_image_workflow(
            self,
            server_roles,
            inst_provisioning_start_page,
            ec2_provisioning_data,
            mgmt_sys_api_clients,
            random_name,
            db_session,
            soap_client):
        '''Test Basic Provisioning Workflow'''
        assert len(server_roles) == len(default_roles) + 1
        inst_provisioning_start_page.click_on_template_item(
            ec2_provisioning_data["image"])
        provision_pg = inst_provisioning_start_page.click_on_continue()
        self.complete_provision_pages_info(ec2_provisioning_data,
            provision_pg, random_name)
        self.assert_vm_state(ec2_provisioning_data, provision_pg,
            "on", random_name)
        self.teardown_remove_from_provider(db_session, soap_client,
            mgmt_sys_api_clients,
            '%s%s' % (ec2_provisioning_data["vm_name"], random_name))

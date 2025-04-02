from django.test import TestCase
from core.models import MutationLog
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from grievance_social_protection.models import Ticket
from grievance_social_protection.schema import Query, Mutation
from grievance_social_protection.tests.gql_payloads import gql_mutation_update_ticket
from grievance_social_protection.tests.test_helpers import create_ticket
from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext


class GQLTicketUpdateTestCase(openIMISGraphQLTestCase):


    user = None

    category = None
    title = None
    resolution = None
    priority = None
    dateOfIncident = None
    channel = None
    flags = None
    status = None
    existing_ticket = None

    @classmethod
    def setUpClass(cls):
        super(GQLTicketUpdateTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='user_authorized', roles=[7])
        cls.existing_ticket = create_ticket(cls.user)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.category = "Default"
        cls.title = "TestMutationUpdate"
        cls.resolution = "2,5"
        cls.priority = "Medium"
        cls.date_of_incident = "2024-11-20"
        cls.channel = "Channel A"
        cls.flags = "Default"
        cls.status = "OPEN"

        cls.gql_client = Client(gql_schema)
        cls.gql_context = BaseTestContext(cls.user)

    def test_update_ticket_success(self):
        mutation_id = "99g453h5g92h04xc66"
        payload = gql_mutation_update_ticket % (
            self.existing_ticket.id,
            self.category,
            self.title,
            self.resolution,
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            self.status,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        ticket = Ticket.objects.get(id=self.existing_ticket.id)
        self.assertEquals(ticket.title, self.title)
        self.assertEquals(ticket.category, self.category)
        self.assertEquals(ticket.resolution, self.resolution)
        self.assertEquals(ticket.priority, self.priority)
        self.assertEquals(str(ticket.date_of_incident), self.date_of_incident)
        self.assertEquals(ticket.flags, self.flags)
        self.assertEquals(ticket.status, self.status)

    def test_update_ticket_false_invalid_resolution_format(self):
        mutation_id = "65g453h4g92h04yf43"
        payload = gql_mutation_update_ticket % (
            self.existing_ticket.id,
            self.category,
            self.title,
            "kjdslkdjslk",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            self.status,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        ticket = Ticket.objects.get(id=self.existing_ticket.id)
        self.assertNotEquals(ticket.title, self.title)

    def test_update_ticket_false_invalid_resolution_day_format(self):
        mutation_id = "65g453h4g92h0zx54"
        payload = gql_mutation_update_ticket % (
            self.existing_ticket.id,
            self.category,
            self.title,
            "99,3",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            self.status,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        ticket = Ticket.objects.get(id=self.existing_ticket.id)
        self.assertNotEquals(ticket.title, self.title)

    def test_update_ticket_false_invalid_resolution_hour_format(self):
        mutation_id = "65g453h4g92h04wl32"
        payload = gql_mutation_update_ticket % (
            self.existing_ticket.id,
            self.category,
            self.title,
            "4,66",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            self.status,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        ticket = Ticket.objects.get(id=self.existing_ticket.id)
        self.assertNotEquals(ticket.title, self.title)

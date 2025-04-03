from django.test import TestCase
from core.models import MutationLog
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from grievance_social_protection.models import Ticket
from grievance_social_protection.schema import Query, Mutation
from grievance_social_protection.tests.gql_payloads import gql_mutation_create_ticket
from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext


class GQLTicketCreateTestCase(openIMISGraphQLTestCase):


    user = None

    category = None
    title = None
    resolution = None
    priority = None
    dateOfIncident = None
    channel = None
    flags = None

    @classmethod
    def setUpClass(cls):
        super(GQLTicketCreateTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='user_authorized', roles=[7])

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.category = "Default"
        cls.title = "TestMutationCreate"
        cls.resolution = "2,5"
        cls.priority = "Medium"
        cls.date_of_incident = "2024-11-20"
        cls.channel = "Channel A"
        cls.flags = "Default"

        cls.gql_client = Client(gql_schema)
        cls.gql_context = BaseTestContext(cls.user)

    def test_create_ticket_success(self):
        mutation_id = "99g453h5g92h04gh88"
        payload = gql_mutation_create_ticket % (
            self.category,
            self.title,
            self.resolution,
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        tickets = Ticket.objects.filter(title=self.title)
        self.assertEquals(tickets.count(), 1)
        ticket = tickets.first()
        self.assertEquals(ticket.title, self.title)
        self.assertEquals(ticket.category, self.category)
        self.assertEquals(ticket.resolution, self.resolution)
        self.assertEquals(ticket.priority, self.priority)
        self.assertEquals(str(ticket.date_of_incident), self.date_of_incident)
        self.assertEquals(ticket.flags, self.flags)

    def test_create_ticket_false_invalid_resolution_format(self):
        mutation_id = "65g453h4g92h04gh98"
        payload = gql_mutation_create_ticket % (
            self.category,
            self.title,
            "kjdslkdjslk",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        tickets = Ticket.objects.filter(title=self.title)
        self.assertEquals(tickets.count(), 0)

    def test_create_ticket_false_invalid_resolution_day_format(self):
        mutation_id = "62g453h4g92h04gh90"
        payload = gql_mutation_create_ticket % (
            self.category,
            self.title,
            "99,3",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        tickets = Ticket.objects.filter(title=self.title)
        self.assertEquals(tickets.count(), 0)

    def test_create_ticket_false_invalid_resolution_hour_format(self):
        mutation_id = "15g453h4g92h04gh92"
        payload = gql_mutation_create_ticket % (
            self.category,
            self.title,
            "4,66",
            self.priority,
            self.date_of_incident,
            self.channel,
            self.flags,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        tickets = Ticket.objects.filter(title=self.title)
        self.assertEquals(tickets.count(), 0)

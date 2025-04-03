from django.test import TestCase
from core.models import MutationLog
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from grievance_social_protection.models import (
    Comment,
    Ticket
)
from grievance_social_protection.schema import Query, Mutation
from grievance_social_protection.tests.gql_payloads import gql_mutation_reopen_ticket
from grievance_social_protection.tests.test_helpers import (
    create_ticket,
    create_comment_for_existing_ticket
)

from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext

class GQLTicketReopenTestCase(openIMISGraphQLTestCase):


    user = None
    status = None
    status_before_reopening = None
    existing_ticket = None
    existing_comment = None

    @classmethod
    def setUpClass(cls):
        super(GQLTicketReopenTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='user_authorized', roles=[7])
        cls.existing_ticket = create_ticket(cls.user)
        cls.existing_comment = create_comment_for_existing_ticket(
            cls.user,
            cls.existing_ticket,
            resolved=True
        )

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.status = "OPEN"
        cls.status_before_reopening = "CLOSED"

        cls.gql_client = Client(gql_schema)
        cls.gql_context = BaseTestContext(cls.user)

    def test_reopen_ticket_success(self):
        mutation_id = "12j123h5g42h04xc66"
        self.assertEquals(self.existing_ticket.status, self.status_before_reopening)
        self.assertEquals(self.existing_comment.is_resolution, True)
        payload = gql_mutation_reopen_ticket % (
            self.existing_ticket.id,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        ticket = Ticket.objects.get(id=self.existing_ticket.id)
        comment = Comment.objects.get(ticket_id=self.existing_ticket.id)
        self.assertEquals(comment.is_resolution, False)
        self.assertEquals(ticket.status, self.status)

from django.apps import apps
from django.test import TestCase

from graphene import Schema
from graphene.test import Client
from core.datetimes.ad_datetime import datetime
from core.models import MutationLog
from core.test_helpers import create_test_interactive_user
from grievance_social_protection.models import Comment
from grievance_social_protection.schema import Query, Mutation
from grievance_social_protection.tests.gql_payloads import (
    gql_mutation_create_comment,
    gql_mutation_create_comment_anonymous_user
)
from grievance_social_protection.tests.test_helpers import create_ticket
from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext
from uuid import uuid4

class GQLTicketCommentCreateTestCase(openIMISGraphQLTestCase):


    user = None

    comment = None
    individual = None
    type = None
    existing_ticket = None

    @classmethod
    def setUpClass(cls):
        super(GQLTicketCommentCreateTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='user_authorized', roles=[7])
        cls.existing_ticket = create_ticket(cls.user)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.comment = "This is an awesome test comment!"
        cls.individual = cls.__create_individual()
        cls.type = "individual"

        cls.gql_client = Client(gql_schema)
        cls.gql_context = BaseTestContext(cls.user)

    def test_create_comment_individual_success(self):
        mutation_id = str(uuid4())
        payload = gql_mutation_create_comment % (
            self.comment,
            self.existing_ticket.id,
            self.individual.id,
            self.type,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        comment = Comment.objects.get(ticket_id=self.existing_ticket.id)
        self.assertEquals(comment.ticket.id, self.existing_ticket.id)
        self.assertEquals(comment.comment, self.comment)
        self.assertEquals(comment.commenter_id, str(self.individual.id))
        self.assertEquals(comment.is_resolution, False)
        self.assertIn(self.type, str(comment.commenter_type))

    def test_create_comment_anonymous_user_success(self):
        mutation_id = str(uuid4())
        payload = gql_mutation_create_comment_anonymous_user % (
            self.comment,
            self.existing_ticket.id,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context.get_request())
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        comment = Comment.objects.get(ticket_id=self.existing_ticket.id)
        self.assertEquals(comment.ticket.id, self.existing_ticket.id)
        self.assertEquals(comment.comment, self.comment)
        self.assertEquals(comment.commenter_id, None)
        self.assertEquals(comment.is_resolution, False)
        self.assertEquals(comment.commenter_type, None)

    @classmethod
    def __create_individual(cls):
        individual_model = apps.get_model('individual', 'Individual')

        add_individual_payload = {
            'first_name': 'TestFN',
            'last_name': 'TestLN',
            'dob': datetime.now(),
            'json_ext': {
                'key': 'value',
                'key2': 'value2'
            }
        }

        object_data = {
            **add_individual_payload
        }

        individual = individual_model(**object_data)
        individual.save(username=cls.user.username)

        return individual

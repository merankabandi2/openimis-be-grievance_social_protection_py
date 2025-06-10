import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from core.gql_queries import UserGQLType
from .apps import TicketConfig
from .models import Ticket, Comment

from core import prefix_filterset, ExtendedConnection
from .util import model_obj_to_json
from .validations import user_associated_with_ticket


def check_ticket_perms(info):
    if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
        raise PermissionDenied(_("unauthorized"))


def check_comment_perms(info):
    user = info.context.user
    if not (user_associated_with_ticket(user) or user.has_perms(TicketConfig.gql_query_comments_perms)):
        raise PermissionDenied(_("Unauthorized"))


class TicketGQLType(DjangoObjectType):
    # TODO on resolve check filters and remove anonymized so user can't fetch ticket using last_name if not visible
    client_mutation_id = graphene.String()
    reporter = graphene.JSONString()
    reporter_type = graphene.Int()
    reporter_type_name = graphene.String()
    is_history = graphene.Boolean()

    reporter_first_name = graphene.String()
    reporter_last_name = graphene.String()
    reporter_dob = graphene.String()

    @staticmethod
    def resolve_reporter_type(root, info):
        check_ticket_perms(info)
        return root.reporter_type.id if root.reporter_type else None

    @staticmethod
    def resolve_reporter_type_name(root, info):
        check_ticket_perms(info)
        return root.reporter_type.name if root.reporter_type else None

    @staticmethod
    def resolve_reporter(root, info):
        check_ticket_perms(info)
        return model_obj_to_json(root.reporter) if root.reporter else None

    @staticmethod
    def resolve_is_history(root, info):
        check_ticket_perms(info)
        return not root.version == Ticket.objects.get(id=root.id).version

    @staticmethod
    def resolve_reporter_first_name(root, info):
        check_ticket_perms(info)
        if root.reporter_type:
            content_type = ContentType.objects.get_for_model(root.reporter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.reporter_id)
                if model_object:
                    if root.reporter_type.name == 'individual':
                        return model_object.first_name
                    elif root.reporter_type.name == 'beneficiary':
                        return model_object.individual.first_name
                    elif root.reporter_type.name == 'user':
                        return None
        return None

    @staticmethod
    def resolve_reporter_last_name(root, info):
        check_ticket_perms(info)
        if root.reporter_type:
            content_type = ContentType.objects.get_for_model(root.reporter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.reporter_id)
                if model_object:
                    if root.reporter_type.name == 'individual':
                        return model_object.last_name
                    elif root.reporter_type.name == 'beneficiary':
                        return model_object.individual.last_name
                    elif root.reporter_type.name == 'user':
                        return None
        return None

    @staticmethod
    def resolve_reporter_dob(root, info):
        check_ticket_perms(info)
        if root.reporter_type:
            content_type = ContentType.objects.get_for_model(root.reporter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.reporter_id)
                if model_object:
                    if root.reporter_type.name == 'individual':
                        return model_object.dob
                    elif root.reporter_type.name == 'beneficiary':
                        return model_object.individual.dob
                    elif root.reporter_type.name == 'user':
                        return None
        return None

    class Meta:
        model = Ticket
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact", "isnull"],
            "version": ["exact"],
            "key": ["exact", "istartswith", "icontains", "iexact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "title": ["exact", "istartswith", "icontains", "iexact"],
            "description": ["exact", "istartswith", "icontains", "iexact"],
            "status": ["exact", "istartswith", "icontains", "iexact"],
            "priority": ["exact", "istartswith", "icontains", "iexact"],
            "category": ["exact", "istartswith", "icontains", "iexact"],
            "flags": ["exact", "istartswith", "icontains", "iexact"],
            "channel": ["exact", "istartswith", "icontains", "iexact"],
            "resolution": ["exact", "istartswith", "icontains", "iexact"],
            'reporter_id': ["exact"],
            "due_date": ["exact", "istartswith", "icontains", "iexact"],
            "date_of_incident": ["exact", "istartswith", "icontains", "iexact"],
            "date_created": ["exact", "istartswith", "icontains", "iexact"],
            **prefix_filterset("attending_staff__", UserGQLType._meta.filter_fields),
        }

        connection_class = ExtendedConnection

    def resolve_client_mutation_id(self, info):
        ticket_mutation = self.mutations.select_related(
            'mutation').filter(mutation__status=0).first()
        return ticket_mutation.mutation.client_mutation_id if ticket_mutation else None


class CommentGQLType(DjangoObjectType):
    commenter = graphene.JSONString()
    commenter_type = graphene.Int()
    commenter_type_name = graphene.String()

    commenter_first_name = graphene.String()
    commenter_last_name = graphene.String()
    commenter_dob = graphene.String()

    @staticmethod
    def resolve_commenter_type(root, info):
        check_comment_perms(info)
        return root.commenter_type.id if root.commenter_type else None

    @staticmethod
    def resolve_commenter_type_name(root, info):
        check_comment_perms(info)
        return root.commenter_type.name if root.commenter_type else None

    @staticmethod
    def resolve_commenter(root, info):
        check_comment_perms(info)
        return model_obj_to_json(root.commenter) if root.commenter else None

    @staticmethod
    def resolve_commenter_first_name(root, info):
        check_comment_perms(info)
        if root.commenter_type:
            content_type = ContentType.objects.get_for_model(root.commenter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.commenter_id)
                if model_object:
                    if root.commenter_type.name == 'individual':
                        return model_object.first_name
                    elif root.commenter_type.name == 'beneficiary':
                        return model_object.individual.first_name
                    elif root.commenter_type.name == 'user':
                        return None
        return None

    @staticmethod
    def resolve_commenter_last_name(root, info):
        check_comment_perms(info)
        if root.commenter_type:
            content_type = ContentType.objects.get_for_model(root.commenter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.commenter_id)
                if model_object:
                    if root.commenter_type.name == 'individual':
                        return model_object.last_name
                    elif root.commenter_type.name == 'beneficiary':
                        return model_object.individual.last_name
                    elif root.commenter_type.name == 'user':
                        return None
        return None

    @staticmethod
    def resolve_commenter_dob(root, info):
        check_comment_perms(info)
        if root.commenter_type:
            content_type = ContentType.objects.get_for_model(root.commenter_type.model_class())
            if content_type:
                model_object = content_type.get_object_for_this_type(pk=root.commenter_id)
                if model_object:
                    if root.commenter_type.name == 'individual':
                        return model_object.dob
                    elif root.commenter_type.name == 'beneficiary':
                        return model_object.individual.dob
                    elif root.commenter_type.name == 'user':
                        return None
        return None

    class Meta:
        model = Comment
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact", "isnull"],
            "comment": ["exact", "istartswith", "icontains", "iexact"],
            "date_created": ["exact", "istartswith", "icontains", "iexact"],
            "is_resolution": ["exact"],
            **prefix_filterset("ticket__", TicketGQLType._meta.filter_fields),
        }

        connection_class = ExtendedConnection


# class TicketAttachmentGQLType(DjangoObjectType):
#     class Meta:
#         model = TicketAttachment
#         interfaces = (graphene.relay.Node,)
#         filter_fields = {
#             "id": ["exact"],
#             "filename": ["exact", "icontains"],
#             "mime_type": ["exact", "icontains"],
#             "url": ["exact", "icontains"],
#             **prefix_filterset("ticket__", TicketGQLType._meta.filter_fields),
#         }
#         connection_class = ExtendedConnection
#
#     @classmethod
#     def get_queryset(cls, queryset, info):
#         queryset = queryset.filter(*filter_validity())
#         return queryset


class AttendingStaffRoleGQLType(ObjectType):
    category = graphene.String()
    role_ids = graphene.List(graphene.String)


class ResolutionTimesByCategoryGQLType(ObjectType):
    category = graphene.String()
    resolution_time = graphene.String()


class GrievanceCategoryGQLType(ObjectType):
    name = graphene.String()
    full_name = graphene.String()
    priority = graphene.String()
    permissions = graphene.JSONString()
    default_flags = graphene.List(graphene.String)
    children = graphene.List(lambda: GrievanceCategoryGQLType)


class GrievanceFlagGQLType(ObjectType):
    name = graphene.String()
    priority = graphene.String()
    permissions = graphene.JSONString()


class GrievanceTypeConfigurationGQLType(ObjectType):
    grievance_types = graphene.List(graphene.String)
    grievance_flags = graphene.List(graphene.String)
    grievance_channels = graphene.List(graphene.String)
    grievance_category_staff_roles = graphene.List(AttendingStaffRoleGQLType)
    grievance_default_resolutions_by_category = graphene.List(ResolutionTimesByCategoryGQLType)
    # Enhanced fields
    grievance_categories_hierarchical = graphene.List(GrievanceCategoryGQLType)
    grievance_flags_detailed = graphene.List(GrievanceFlagGQLType)
    accessible_categories = graphene.List(graphene.String)
    accessible_flags = graphene.List(graphene.String)

    def resolve_grievance_types(self, info):
        # Return accessible categories in flat format for backward compatibility
        from .access_control import GrievanceAccessControl
        user = info.context.user
        return GrievanceAccessControl.get_accessible_categories(user)

    def resolve_grievance_flags(self, info):
        # Return accessible flags
        from .access_control import GrievanceAccessControl
        user = info.context.user
        return GrievanceAccessControl.get_accessible_flags(user)

    def resolve_grievance_channels(self, info):
        return TicketConfig.grievance_channels
    
    def resolve_grievance_categories_hierarchical(self, info):
        """Return hierarchical category structure with access control"""
        from .access_control import GrievanceAccessControl
        user = info.context.user
        hierarchy = GrievanceAccessControl.get_category_hierarchy(user)
        
        def build_gql_category(cat_dict):
            """Convert dict to GQL type"""
            children = [build_gql_category(child) for child in cat_dict.get('children', [])]
            return GrievanceCategoryGQLType(
                name=cat_dict['name'],
                full_name=cat_dict.get('full_name', cat_dict['name']),
                priority=cat_dict.get('priority', 'Medium'),
                permissions=cat_dict.get('permissions', {}),
                default_flags=cat_dict.get('default_flags', []),
                children=children
            )
        
        return [build_gql_category(cat) for cat in hierarchy]
    
    def resolve_grievance_flags_detailed(self, info):
        """Return detailed flag information with access control"""
        from .access_control import GrievanceAccessControl
        from .apps import TicketConfig
        
        user = info.context.user
        accessible_flags = GrievanceAccessControl.get_accessible_flags(user)
        processed_flags = getattr(TicketConfig, 'processed_flags', {})
        
        flags = []
        for flag_name in accessible_flags:
            flag_info = processed_flags.get(flag_name, {})
            flags.append(GrievanceFlagGQLType(
                name=flag_name,
                priority=flag_info.get('priority', 'Medium'),
                permissions=flag_info.get('permissions', {})
            ))
        
        return flags
    
    def resolve_accessible_categories(self, info):
        """Return flat list of accessible categories for create operations"""
        from .access_control import GrievanceAccessControl
        user = info.context.user
        return GrievanceAccessControl.get_accessible_categories(user)
    
    def resolve_accessible_flags(self, info):
        """Return flat list of accessible flags for use operations"""
        from .access_control import GrievanceAccessControl
        user = info.context.user
        return GrievanceAccessControl.get_accessible_flags(user)

    def resolve_grievance_category_staff_roles(self, info):
        category_staff_role_list = []
        for category_key, role_ids in TicketConfig.default_attending_staff_role_ids.items():
            category_staff_role = AttendingStaffRoleGQLType(
                category=category_key,
                role_ids=role_ids
            )
            category_staff_role_list.append(category_staff_role)

        return category_staff_role_list

    def resolve_grievance_default_resolutions_by_category(self, info):
        category_resolution_time_list = []
        for category_key, resolution_time in TicketConfig.default_resolution.items():
            category_resolution_time = ResolutionTimesByCategoryGQLType(
                category=category_key,
                resolution_time=resolution_time
            )
            category_resolution_time_list.append(category_resolution_time)

        return category_resolution_time_list

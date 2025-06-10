import graphene
from django.contrib.auth.models import AnonymousUser

from core.schema import OrderedDjangoFilterConnectionField
from core.schema import signal_mutation_module_validate
from django.db.models import Q, Count, F
from django.db.models.functions import TruncMonth
import graphene_django_optimizer as gql_optimizer
import json

from core.utils import append_validity_filter
from .apps import MODULE_NAME

from .gql_queries import *
from .gql_mutations import *
from django.utils.translation import gettext_lazy as _


class StatusAggregationType(graphene.ObjectType):
    status = graphene.String()
    count = graphene.Int()


class CategoryAggregationType(graphene.ObjectType):
    category = graphene.String()
    count = graphene.Int()


class ChannelAggregationType(graphene.ObjectType):
    channel = graphene.String()
    count = graphene.Int()


class PriorityAggregationType(graphene.ObjectType):
    priority = graphene.String()
    count = graphene.Int()


class MonthlyAggregationType(graphene.ObjectType):
    month = graphene.String()
    count = graphene.Int()


class GenderAggregationType(graphene.ObjectType):
    gender = graphene.String()
    count = graphene.Int()


class TicketAggregationType(graphene.ObjectType):
    total_count = graphene.Int()
    status_distribution = graphene.List(StatusAggregationType)
    category_distribution = graphene.List(CategoryAggregationType)
    channel_distribution = graphene.List(ChannelAggregationType)
    priority_distribution = graphene.List(PriorityAggregationType)
    monthly_distribution = graphene.List(MonthlyAggregationType)
    gender_distribution = graphene.List(GenderAggregationType)
    
    # Raw category distribution (not grouped)
    raw_category_distribution = graphene.List(CategoryAggregationType)
    
    # Summary stats
    open_count = graphene.Int()
    pending_count = graphene.Int()
    in_progress_count = graphene.Int()
    resolved_count = graphene.Int()
    closed_count = graphene.Int()
    sensitive_count = graphene.Int()
    avg_resolution_days = graphene.Float()
    

class Query(graphene.ObjectType):
    tickets = OrderedDjangoFilterConnectionField(
        TicketGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        show_history=graphene.Boolean(),
        client_mutation_id=graphene.String(),
        ticket_version=graphene.Int(),
    )

    ticketsStr = OrderedDjangoFilterConnectionField(
        TicketGQLType,
        str=graphene.String(),
    )
    # ticket_attachments = DjangoFilterConnectionField(TicketAttachmentGQLType)

    ticket_details = OrderedDjangoFilterConnectionField(
        TicketGQLType,
        # showHistory=graphene.Boolean(),
        orderBy=graphene.List(of_type=graphene.String),
    )

    grievance_config = graphene.Field(GrievanceTypeConfigurationGQLType)

    comments = OrderedDjangoFilterConnectionField(
        CommentGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )
    
    tickets_aggregation = graphene.Field(
        TicketAggregationType,
        status=graphene.String(),
        category=graphene.String(),
        channel=graphene.String(),
        priority=graphene.String(),
        date_received_gte=graphene.DateTime(),
        date_received_lte=graphene.DateTime(),
    )

    def resolve_comments(self, info, **kwargs):
        user = info.context.user

        if not (user_associated_with_ticket(user) or user.has_perms(TicketConfig.gql_query_comments_perms)):
            raise PermissionDenied(_("Unauthorized"))

        return gql_optimizer.query(Comment.objects.all(), info)

    def resolve_ticket_details(self, info, **kwargs):
        if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
            raise PermissionDenied(_("unauthorized"))
        
        query = Ticket.objects.filter(*append_validity_filter(**kwargs)).all().order_by('ticket_title', )
        
        # Apply category and flag permission filtering
        from .access_control import GrievanceAccessControl
        query = GrievanceAccessControl.filter_ticket_queryset(query, info.context.user)
        
        return gql_optimizer.query(query, info)

    def resolve_tickets(self, info, **kwargs):
        """
        Extra steps to perform when Scheme is queried
        """
        # Check if user has permission
        if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
            raise PermissionDenied(_("unauthorized"))
        filters = []
        model = Ticket

        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        # Used to specify if user want to see all records including invalid records as history
        show_history = kwargs.get('show_history', False)
        ticket_version = kwargs.get('ticket_version', False)
        if show_history or ticket_version:
            if ticket_version:
                filters.append(Q(version=ticket_version))
            query = model.history.filter(*filters).all().as_instances()
        else:
            query = model.objects.filter(*filters, is_deleted=False).all()

        # Apply category and flag permission filtering
        from .access_control import GrievanceAccessControl
        query = GrievanceAccessControl.filter_ticket_queryset(query, info.context.user)

        return gql_optimizer.query(query, info)

    def resolve_ticketsStr(self, info, **kwargs):
        """
        Extra steps to perform when Scheme is queried
        """
        # Check if user has permission
        if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
            raise PermissionDenied(_("unauthorized"))
        filters = []

        # Used to specify if user want to see all records including invalid records as history
        show_history = kwargs.get('show_history', False)
        if not show_history:
            filters += append_validity_filter(**kwargs)

        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        # str = kwargs.get('str')
        # if str is not None:
        #     filters += [Q(code__icontains=str) | Q(name__icontains=str)]

        query = Ticket.objects.filter(*filters).all()
        
        # Apply category and flag permission filtering
        from .access_control import GrievanceAccessControl
        query = GrievanceAccessControl.filter_ticket_queryset(query, info.context.user)

        return gql_optimizer.query(query, info)

    # def resolve_claim_attachments(self, info, **kwargs):
    #     if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
    #         raise PermissionDenied(_("unauthorized"))


    def resolve_grievance_config(self, info, **kwargs):
        user = info.context.user
        if type(user) is AnonymousUser:
            raise PermissionDenied(_("unauthorized"))
        if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
            raise PermissionDenied(_("unauthorized"))
        return GrievanceTypeConfigurationGQLType()
    
    def resolve_tickets_aggregation(self, info, **kwargs):
        """
        Resolve ticket aggregations with filtering
        """
        from datetime import datetime, timedelta
        from django.db.models import Avg
        
        # Check permissions
        if not info.context.user.has_perms(TicketConfig.gql_query_tickets_perms):
            raise PermissionDenied(_("unauthorized"))
        
        # Base queryset
        queryset = Ticket.objects.filter(is_deleted=False)
        
        # Apply filters
        if kwargs.get('status'):
            queryset = queryset.filter(status=kwargs['status'])
        
        if kwargs.get('channel'):
            queryset = queryset.filter(channel=kwargs['channel'])
            
        if kwargs.get('priority'):
            queryset = queryset.filter(priority=kwargs['priority'])
            
        if kwargs.get('date_received_gte'):
            queryset = queryset.filter(date_created__gte=kwargs['date_received_gte'])
            
        if kwargs.get('date_received_lte'):
            queryset = queryset.filter(date_created__lte=kwargs['date_received_lte'])
            
        # Category filter with JSON array handling
        if kwargs.get('category'):
            category_filter = kwargs['category']
            queryset = queryset.filter(
                Q(category=category_filter) |
                Q(category__icontains=f'["{category_filter}"') |
                Q(category__icontains=f'"{category_filter}",') |
                Q(category__icontains=f',"{category_filter}"')
            )
        
        # Status distribution
        status_counts = queryset.values('status').annotate(count=Count('id')).order_by('status')
        status_distribution = [
            StatusAggregationType(status=item['status'] or 'UNKNOWN', count=item['count'])
            for item in status_counts
        ]
        
        # Category distribution - handle JSON arrays and space-separated values
        
        # Define category mappings
        sensitive_categories = ['violence_vbg', 'corruption', 'accident_negligence', 'discrimination_ethnie_religion']
        special_categories = ['erreur_exclusion', 'erreur_inclusion', 'maladie_mentale']
        non_sensitive_categories = ['non_paiement', 'paiement', 'telephone_non_recu', 'telephone', 
                                   'compte', 'assistance_conseil', 'information', 'autre']
        
        # Count parent categories directly from the queryset
        cas_sensibles_filter = Q()
        cas_speciaux_filter = Q()
        cas_non_sensibles_filter = Q()
        
        for cat in sensitive_categories:
            cas_sensibles_filter |= Q(category=cat)
            cas_sensibles_filter |= Q(category__icontains=f'["{cat}"')
            cas_sensibles_filter |= Q(category__contains=f' {cat}')
            cas_sensibles_filter |= Q(category__startswith=f'{cat} ')
            cas_sensibles_filter |= Q(category__endswith=f' {cat}')
        
        for cat in special_categories:
            cas_speciaux_filter |= Q(category=cat)
            cas_speciaux_filter |= Q(category__icontains=f'["{cat}"')
            cas_speciaux_filter |= Q(category__contains=f' {cat}')
            cas_speciaux_filter |= Q(category__startswith=f'{cat} ')
            cas_speciaux_filter |= Q(category__endswith=f' {cat}')
            
        for cat in non_sensitive_categories:
            cas_non_sensibles_filter |= Q(category=cat)
            cas_non_sensibles_filter |= Q(category__icontains=f'["{cat}"')
            cas_non_sensibles_filter |= Q(category__contains=f' {cat}')
            cas_non_sensibles_filter |= Q(category__startswith=f'{cat} ')
            cas_non_sensibles_filter |= Q(category__endswith=f' {cat}')
        
        # Count each parent category
        # For cas_sensibles, also include tickets with SENSITIVE flag
        cas_sensibles_count = queryset.filter(cas_sensibles_filter | Q(flags__icontains='SENSITIVE')).count()
        
        # For cas_speciaux, exclude tickets with SENSITIVE flag (they're already in cas_sensibles)
        cas_speciaux_count = queryset.filter(cas_speciaux_filter).exclude(flags__icontains='SENSITIVE').exclude(cas_sensibles_filter).count()
        
        # For cas_non_sensibles, exclude tickets with SENSITIVE flag and those already in other categories
        cas_non_sensibles_count = queryset.filter(cas_non_sensibles_filter).exclude(flags__icontains='SENSITIVE').exclude(cas_sensibles_filter).exclude(cas_speciaux_filter).count()
        
        # No category - exclude all categorized tickets
        no_category_count = queryset.filter(
            Q(category__isnull=True) | Q(category='') | Q(category='[]')
        ).exclude(flags__icontains='SENSITIVE').count()
        
        # Build category distribution with parent categories
        category_counts = {
            'cas_sensibles': cas_sensibles_count,
            'cas_speciaux': cas_speciaux_count,
            'cas_non_sensibles': cas_non_sensibles_count,
            'no_category': no_category_count,
        }
        
        # Also get raw category distribution
        category_raw = queryset.values('category').annotate(count=Count('id'))
        raw_category_counts = {}
        
        for item in category_raw:
            cat = item['category']
            count = item['count']
            
            if not cat or cat == '[]' or cat == '':
                raw_category_counts['no_category'] = raw_category_counts.get('no_category', 0) + count
            else:
                # Extract categories
                categories = []
                try:
                    # Try to parse as JSON array first
                    if cat and cat.startswith('['):
                        parsed = json.loads(cat)
                        if isinstance(parsed, list):
                            categories = parsed
                    else:
                        # Otherwise treat as space-separated values
                        categories = cat.split()
                except Exception as e:
                    # If all parsing fails, treat as space-separated
                    categories = cat.split()
                
                # If no categories extracted, treat as single value
                if not categories:
                    categories = [cat]
                
                # Process each category
                for single_cat in categories:
                    single_cat = single_cat.strip()
                    if single_cat:
                        # Add to raw counts
                        raw_category_counts[single_cat] = raw_category_counts.get(single_cat, 0) + count
        
        category_distribution = [
            CategoryAggregationType(category=cat, count=count)
            for cat, count in category_counts.items()
        ]
        
        raw_category_distribution = [
            CategoryAggregationType(category=cat, count=count)
            for cat, count in raw_category_counts.items()
        ]
        
        # Channel distribution - handle space-separated values
        channel_raw = queryset.values('channel').annotate(count=Count('id'))
        channel_counts = {}
        
        for item in channel_raw:
            chan = item['channel']
            count = item['count']
            
            if not chan:
                channel_counts['UNKNOWN'] = channel_counts.get('UNKNOWN', 0) + count
            else:
                # Extract channels (space-separated)
                channels = chan.split()
                
                # If no channels extracted, treat as single value
                if not channels:
                    channels = [chan]
                
                # Process each channel
                for single_chan in channels:
                    single_chan = single_chan.strip()
                    if single_chan and single_chan != 'autre':  # Skip 'autre' as it's not meaningful
                        channel_counts[single_chan] = channel_counts.get(single_chan, 0) + count
        
        channel_distribution = [
            ChannelAggregationType(channel=chan, count=count)
            for chan, count in channel_counts.items()
        ]
        
        # Priority distribution
        priority_counts = queryset.values('priority').annotate(count=Count('id')).order_by('priority')
        priority_distribution = [
            PriorityAggregationType(priority=item['priority'] or 'NORMAL', count=item['count'])
            for item in priority_counts
        ]
        
        # Monthly distribution
        monthly_counts = queryset.annotate(
            month=TruncMonth('date_created')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        monthly_distribution = [
            MonthlyAggregationType(
                month=item['month'].strftime('%Y-%m') if item['month'] else 'Unknown',
                count=item['count']
            )
            for item in monthly_counts
        ]
        
        # Gender distribution - extract from reporter JSON
        gender_counts = {'M': 0, 'F': 0, 'OTHER': 0, 'UNKNOWN': 0}
        
        for ticket in queryset.only('reporter'):
            gender = None
            if ticket.reporter:
                try:
                    reporter_data = json.loads(ticket.reporter)
                    gender = reporter_data.get('gender') or reporter_data.get('individual', {}).get('gender')
                except:
                    pass
            
            if gender in ['M', 'homme']:
                gender_counts['M'] += 1
            elif gender in ['F', 'femme']:
                gender_counts['F'] += 1
            elif gender:
                gender_counts['OTHER'] += 1
            else:
                gender_counts['UNKNOWN'] += 1
        
        gender_distribution = [
            GenderAggregationType(gender=gender, count=count)
            for gender, count in gender_counts.items() if count > 0
        ]
        
        # Calculate summary stats
        total_count = queryset.count()
        open_count = queryset.filter(status='OPEN').count()
        pending_count = queryset.filter(status='PENDING').count()
        in_progress_count = queryset.filter(status='IN_PROGRESS').count()
        resolved_count = queryset.filter(status='RESOLVED').count()
        closed_count = queryset.filter(status='CLOSED').count()
        
        # Sensitive count - check both flags and category
        # Combine the cas_sensibles_filter with the SENSITIVE flag
        sensitive_filter = cas_sensibles_filter | Q(flags__icontains='SENSITIVE')
        sensitive_count = queryset.filter(sensitive_filter).count()
        
        # Average resolution time
        resolved_tickets = queryset.filter(
            status='RESOLVED',
            date_updated__isnull=False
        )
        
        avg_resolution_days = 0
        if resolved_tickets.exists():
            resolution_times = []
            for ticket in resolved_tickets:
                if ticket.date_created and ticket.date_updated:
                    days = (ticket.date_updated - ticket.date_created).days
                    resolution_times.append(days)
            
            if resolution_times:
                avg_resolution_days = sum(resolution_times) / len(resolution_times)
        
        return TicketAggregationType(
            total_count=total_count,
            status_distribution=status_distribution,
            category_distribution=category_distribution,
            raw_category_distribution=raw_category_distribution,
            channel_distribution=channel_distribution,
            priority_distribution=priority_distribution,
            monthly_distribution=monthly_distribution,
            gender_distribution=gender_distribution,
            open_count=open_count,
            pending_count=pending_count,
            in_progress_count=in_progress_count,
            resolved_count=resolved_count,
            closed_count=closed_count,
            sensitive_count=sensitive_count,
            avg_resolution_days=avg_resolution_days
        )


class Mutation(graphene.ObjectType):
    create_Ticket = CreateTicketMutation.Field()
    update_Ticket = UpdateTicketMutation.Field()
    delete_Ticket = DeleteTicketMutation.Field()

    create_comment = CreateCommentMutation.Field()

    resolve_grievance_by_comment = ResolveGrievanceByCommentMutation.Field()
    reopen_ticket = ReopenTicketMutation.Field()

    # create_ticket_attachment = CreateTicketAttachmentMutation.Field()
    # update_ticket_attachment = UpdateTicketAttachmentMutation.Field()


def on_bank_mutation(kwargs, k='uuid'):
    """
    This method is called on signal binding for scheme mutation
    """

    # get uuid from data
    ticket_uuid = kwargs['data'].get('uuid', None)
    if not ticket_uuid:
        return []
    # fetch the scheme object by uuid
    impacted_ticket = Ticket.objects.get(Q(uuid=ticket_uuid))
    # Create a mutation object
    TicketMutation.objects.create(Bank=impacted_ticket, mutation_id=kwargs['mutation_log_id'])
    return []


def on_ticket_mutation(**kwargs):
    uuids = kwargs["data"].get("uuids", [])
    if not uuids:
        uuid = kwargs["data"].get("claim_uuid", None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []
    impacted_tickets = Ticket.objects.filter(uuid__in=uuids).all()
    for ticket in impacted_tickets:
        TicketMutation.objects.create(Ticket=ticket, mutation_id=kwargs["mutation_log_id"])
    return []


def bind_signals():
    signal_mutation_module_validate[MODULE_NAME].connect(on_ticket_mutation)

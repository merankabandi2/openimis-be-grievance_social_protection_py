import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

MODULE_NAME = "grievance_social_protection"

DEFAULT_STRING = 'Default'
# CRON timedelta: {days},{hours}
DEFAULT_TIME_RESOLUTION = '5,0'

DEFAULT_CFG = {
    "default_validations_disabled": False,
    "gql_query_tickets_perms": ["127000"],
    "gql_query_comments_perms": ["127004"],
    "gql_mutation_create_tickets_perms": ["127001"],
    "gql_mutation_update_tickets_perms": ["127002"],
    "gql_mutation_delete_tickets_perms": ["127003"],
    "gql_mutation_create_comment_perms": ["127005"],
    "gql_mutation_resolve_grievance_perms": ["127006"],
    "tickets_attachments_root_path": None,

    # Main grievance categories from form
    "grievance_types": [
        DEFAULT_STRING, 
        # Sensitive categories
        "violence_vbg", 
        "corruption", 
        "accident_negligence", 
        "discrimination_ethnie_religion", 
        # Special categories
        "erreur_exclusion", 
        "erreur_inclusion", 
        "maladie_mentale", 
        # Non-sensitive categories
        "paiement", 
        "telephone", 
        "compte", 
        "information"
    ],
    
    # Flags for sensitive/special cases
    "grievance_flags": [
        DEFAULT_STRING, 
        "SENSITIVE", 
        "SPECIAL"
    ],
    
    # Communication channels
    "grievance_channels": [
        DEFAULT_STRING, 
        "telephone", 
        "sms", 
        "en_personne", 
        "courrier_simple", 
        "courrier_electronique", 
        "ligne_verte", 
        "boite_suggestion", 
        "autre"
    ],
    
    # VBG subcategories
    "vbg_types": [
        "viol",
        "mariage_force_precoce",
        "violence_abus",
        "sante_maternelle",
        "autre",
        "autre_"
    ],
    
    # Exclusion error subcategories
    "exclusion_types": [
        "demande_insertion",
        "probleme_identification",
        "autre"
    ],
    
    # Payment problem subcategories
    "payment_types": [
        "paiement_pas_recu",
        "paiement_en_retard",
        "paiement_incomplet",
        "vole",
        "autre"
    ],
    
    # Phone problem subcategories
    "phone_types": [
        "perdu",
        "pas_de_reseau",
        "allume_pas_batterie",
        "recoit_pas_tm",
        "mot_de_passe_oublie",
        "autre"
    ],
    
    # Account problem subcategories
    "account_types": [
        "non_active",
        "bloque",
        "autre"
    ],
    
    # Beneficiary types
    "beneficiary_types": [
        "ordinaire",
        "securite_alimentaire_cerc",
        "chocs_climatiques",
        "autre"
    ],

    "default_responses": {DEFAULT_STRING: DEFAULT_STRING},
    "grievance_anonymized_fields": {DEFAULT_STRING: []},
    # CRON timedelta: {days},{hours}
    "resolution_times": DEFAULT_TIME_RESOLUTION,
    "default_resolution": {
        DEFAULT_STRING: DEFAULT_TIME_RESOLUTION, 
        # Sensitive cases (high priority)
        "violence_vbg": "2,0", 
        "corruption": "3,0", 
        # Special cases (medium priority)
        "erreur_exclusion": "4,0", 
        "erreur_inclusion": "4,0", 
        "maladie_mentale": "3,0", 
        # Non-sensitive cases (normal priority)
        "paiement": "5,0", 
        "telephone": "5,0", 
        "compte": "5,0", 
        "information": "3,0"
    },

    "attending_staff_role_ids": [],
    "default_attending_staff_role_ids": {DEFAULT_STRING: [1, 2]},
}


class TicketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = MODULE_NAME
    gql_query_tickets_perms = []
    gql_query_comments_perms = []
    gql_mutation_create_tickets_perms = []
    gql_mutation_update_tickets_perms = []
    gql_mutation_delete_tickets_perms = []
    gql_mutation_resolve_grievance_perms = []
    gql_mutation_create_comment_perms = []
    tickets_attachments_root_path = None

    grievance_types = []
    grievance_flags = []
    grievance_channels = []
    default_responses = {}
    grievance_anonymized_fields = {}
    resolution_times = {}
    default_resolution = {}
    attending_staff_role_ids = []
    default_attending_staff_role_ids = {}

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self.__validate_grievance_dict_fields(cfg, 'default_responses')
        self.__validate_grievance_dict_fields(cfg, 'grievance_anonymized_fields')
        self.__validate_grievance_dict_fields(cfg, 'default_resolution')
        self.__validate_grievance_default_resolution_time(cfg)
        self.__load_config(cfg)

    @classmethod
    def __validate_grievance_dict_fields(cls, cfg, field_name):
        def get_grievance_type_options_msg(types):
            types_string = ", ".join(types)
            return logger.info(f'Available grievance types: {types_string}')

        dict_field = cfg.get(field_name, {})
        if not dict_field:
            return

        grievance_types = cfg.get('grievance_types', [])
        if not grievance_types:
            logger.warning('Please specify grievance_types if you want to setup %s.', field_name)

        if not isinstance(dict_field, dict):
            get_grievance_type_options_msg(grievance_types)
            return

        for field_key in dict_field.keys():
            if field_key not in grievance_types:
                logger.warning('%s in %s not in grievance_types', field_key, field_name)
                get_grievance_type_options_msg(grievance_types)

    @classmethod
    def __validate_grievance_default_resolution_time(cls, cfg):
        dict_field = cfg.get("default_resolution", {})
        if not dict_field:
            return
        for key in dict_field:
            value = dict_field[key]
            if value in ['', None]:
                resolution_times = cfg.get("resolution_times", DEFAULT_TIME_RESOLUTION)
                logger.warning(
                    '"%s" has no value for resolution. The default one is taken as "%s".',
                    key,
                    resolution_times
                )
                dict_field[key] = resolution_times
            else:
                if ',' not in value:
                    logger.warning("Invalid input. Configuration should contain two integers "
                                   "representing days and hours, separated by a comma.")
                else:
                    parts = value.split(',')
                    # Parse days and hours
                    days = int(parts[0])
                    hours = int(parts[1])
                    # Validate days and hours
                    if 0 <= days < 99 and 0 <= hours < 24:
                        logger.info(f"Days: {days}, Hours: {hours}")
                    else:
                        logger.warning("Invalid input. Days must be between 0 and 99, "
                                       "and hours must be between 0 and 24.")

    @classmethod
    def __load_config(cls, cfg):
        """
        Load all config fields that match current AppConfig class fields, all custom fields have to be loaded separately
        """
        for field in cfg:
            if hasattr(TicketConfig, field):
                setattr(TicketConfig, field, cfg[field])

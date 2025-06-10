# openIMIS Backend Grievance Social Protection reference module
This repository holds the files of the openIMIS Backend grievance social protection reference module.
It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py).

## Features

- **Ticket Management**: Create, update, and track grievance tickets
- **Comments System**: Add comments and resolutions to tickets
- **Configurable Categories and Flags**: Define custom grievance types and flags
- **Rights-Based Access Control**: Fine-grained permissions for categories and flags
- **Hierarchical Categories**: Support for multi-level category structures
- **Priority Management**: Automatic priority assignment based on category/flag configuration
- **Resolution Tracking**: Configure resolution times by category

## Configuration options (can be changed via core.ModuleConfiguration)

### Basic Configuration

* `resolution_times`: Default time to resolution in form of CRON timedelta: `{days},{hours}` where days are values between <0, 99) and hours are between 0 and 24. 
(default: `5,0`)

* `default_resolution`: The field will be in form of the JSON dictionary with pairs like: 
Key - type of the grievance, 
Value - time to resolution in form of CRON timedelta: `{days},{hours}` where days are values between <0, 99) and hours are between 0 and 24.
(default: `{Default: '5,0'}`)
Note: If for given type of the grievance time is not provided then default value is used from `resolution_times`.

### Categories Configuration

The module supports both simple and enhanced category configurations:

#### Simple Format (backward compatible)
```json
{
  "grievance_types": ["complaint", "feedback", "appeal"]
}
```

#### Enhanced Format with Permissions and Resolution Times
```json
{
  "grievance_types": [
    "simple_category",
    {
      "name": "complaint",
      "priority": "High",
      "permissions": ["127001", "127002"],  // Grants all access to users with either permission
      "default_flags": ["urgent"],
      "resolution_times": "3,0",  // 3 days, 0 hours
      "children": [
        {
          "name": "service_complaint",
          "permissions": ["127003"],  // Child can override with its own permissions
          "resolution_times": "2,12"  // Overrides parent's resolution time
        },
        {
          "name": "general_complaint"
          // Inherits parent's resolution_times (3,0) and permissions
        }
      ]
    }
  ]
}
```

##### Resolution Times Priority
Resolution times are determined in the following order:
1. Category-specific `resolution_times` (with inheritance from parent categories)
2. Legacy `default_resolution` configuration for the category
3. Global `resolution_times` configuration
4. Default value `5,0` (5 days, 0 hours)

##### Example Configuration
```json
{
  "resolution_times": "5,0",  // Global default: 5 days
  "default_resolution": {     // Legacy configuration (still supported)
    "feedback": "7,0"
  },
  "grievance_types": [
    {
      "name": "complaint",
      "resolution_times": "3,0",  // Category-specific: 3 days
      "children": [
        {
          "name": "urgent_complaint",
          "resolution_times": "1,0"  // Override: 1 day
        },
        {
          "name": "general_complaint"  // Inherits parent's 3 days
        }
      ]
    },
    "feedback"  // Uses default_resolution: 7 days
  ]
}

### Flags Configuration

Similarly, flags support both simple and enhanced formats:

#### Simple Format
```json
{
  "grievance_flags": ["urgent", "sensitive"]
}
```

#### Enhanced Format with Permissions
```json
{
  "grievance_flags": [
    "public",
    {
      "name": "sensitive",
      "priority": "Critical",
      "permissions": ["127004", "127005"]  // Grants all access
    }
  ]
}
```

## Permissions

The module uses Django's permission system for access control:

### Query Permissions (Numeric codes for backward compatibility)
- `127000`: View tickets
- `127001`: Create tickets
- `127002`: Update tickets
- `127003`: Delete tickets
- `127004`: View comments
- `127005`: Create comments
- `127006`: Resolve grievances

### Category and Flag Permissions
Categories and flags can be restricted using the system's numeric permission codes. When permissions are specified as a list (e.g., `["127001", "127002"]`), having ANY permission in the list grants full access to all operations (view, create, edit/use).

- Child categories inherit parent permissions unless explicitly overridden
- Ticket queries are automatically filtered based on user permissions

## GraphQL API

### Queries
- `tickets`: List all accessible tickets (filtered by permissions)
- `ticketsStr`: String-based ticket search
- `ticket_details`: Detailed ticket information
- `grievance_config`: Get configuration including accessible categories/flags
- `comments`: List ticket comments

### Mutations
- `createTicket`: Create a new grievance ticket
- `updateTicket`: Update existing ticket
- `deleteTicket`: Delete a ticket
- `createComment`: Add comment to ticket
- `resolveGrievanceByComment`: Resolve ticket with comment
- `reopenTicket`: Reopen a closed ticket

### Configuration Query Fields
The `grievance_config` query returns:
- `grievance_types`: Flat list of accessible categories
- `grievance_flags`: List of accessible flags
- `grievance_channels`: Available channels
- `grievance_categories_hierarchical`: Hierarchical category structure
- `grievance_flags_detailed`: Detailed flag information with permissions
- `accessible_categories`: Categories user can create tickets in
- `accessible_flags`: Flags user can apply to tickets

## Access Control Features

1. **Category-Based Filtering**: Users only see tickets in categories they have permission to view
2. **Flag-Based Filtering**: Tickets with restricted flags are hidden from unauthorized users
3. **Hierarchical Permissions**: 
   - Children inherit parent permissions by default
   - Children can override with more restrictive permissions
   - Users see only accessible parts of the hierarchy
4. **Create/Update Validation**: System validates permissions before allowing ticket operations

## Testing

The module includes comprehensive tests for all permission scenarios:
```bash
python manage.py test grievance_social_protection.tests.test_access_control
python manage.py test grievance_social_protection.tests.test_config_processing
python manage.py test grievance_social_protection.tests.test_ticket_service_permissions
python manage.py test grievance_social_protection.tests.test_ticket_query_filtering
``` 

### ER-Diagram

erDiagram
    INITIATIVE ||--o{ ACTIVITY : contains
    INITIATIVE ||--o{ INITIATIVE_ROLES : gives_access
    %% We import payments from BNG without necessarily assigning them to an initiative.
    INITIATIVE |o--o{ PAYMENT : linked_to
    ACTIVITY ||--o{ ACTIVITY_ROLES : gives_access
    USER ||--o{ ACTIVITY_ROLES : has
    USER ||--o{ INITIATIVE_ROLES : has
    %% We import payments from BNG without necessarily assigning them to an initiative.
    ACTIVITY |o--o{ PAYMENT : linked_to
    ATTACHMENT }o--|| PAYMENT : attached_to
    BNG_ACCOUNT |o--|| USER : created_by
    DEBIT_CARD |o--o{ PAYMENT : linked_to
    DEBIT_CARD }o--o| INITIATIVE : linked_to
    REQUISITION }o--|| USER : created_by
    BANK_ACCOUNT }o--|| REQUISITION : linked_to
    PAYMENT }o--o| BANK_ACCOUNT : linked_to
    USER ||--o{ BANK_ACCOUNT_ROLES : gives_access
    BANK_ACCOUNT || --|{ BANK_ACCOUNT_ROLES: gives_access
    FUNDER ||--o{ REGULATION : issues
    REGULATION ||--o{ GRANT : part_of
    REGULATION_ROLES }o--o{ USER : has
    REGULATION }o--o{ REGULATION_ROLES : gives_access_to
    %% What type of relationship should this be?
    GRANT }|--o{ INITIATIVE : part_of
    ACCOUNTABILITY_REPORT |o--|| GRANT : reports_on
    USER ||--o{ PAYMENT_IMPORT : done_by

    
    REGULATION_ROLES {
        int user_id
        int grant_id
        %% subsidy_officer, policy_officer or overseer
        str role
    }

    BANK_ACCOUNT_ROLES {
        int user_id
        int bank_account_id
        %% owner, sharer
        str role
    }

    INITIATIVE_ROLES {
        int user_id
        int initiative_id
    }

    ACTIVITY_ROLES {
        int user_id
        int activity_id
    }

    MUTATION_LOGS {
        str what
        str who
        str when
    }

    USER {
        int id
        str first_name
        str last_name
        str biography
        str role
        str image
        bool deleted
        bool hidden
    }

    BNG_ACCOUNT {
        int id
        str iban
        datetime expires_on
        str consent_id
        str access_token
        datetime last_import_on
        int user_id
    }

    INITIATIVE {
        int id
        str name
        str description
        str purpose
        str target_audience
        str owner
        str owner_email
        str legal_entity
        str address_applicant
        str kvk_registration
        str location
        str image
        bool hidden_sponsors
        bool hidden
        int grant_id
    }

    ACTIVITY {
        int id
        str name
        str description
        str purpose
        str target_audience
        str image
        bool hidden
        bool finished
        str finished_description
    }

    PAYMENT {
        int id
        str transaction_id
        str entry_reference
        str end_to_end_id
        datetime booking_date
        Decimal transaction_amount
        str creditor_name
        str creditor_account
        str debtor_name
        str debtor_account
        Route route
        PaymentType type
        str remittance_information_unstructured
        str remittance_information_structured
        str short_user_description
        str long_user_description
    }

    DEBIT_CARD {
        int id
        str card_number
    }

    REQUISITION {
        int id
        str institution_id
        str api_requisition_id
        str reference_id
        bool callback_handled
        ReqStatus status
    }

    BANK_ACCOUNT {
        int id
        str api_account_id
        str iban
        str name
        datetime created
        datetime last_accessed
    }

    REGULATION {
        int id
        str name
        str description
    }

    GRANT {
        int id
        str name
        str reference
        Decimal budget
    }

    FUNDER {
        int id
        str name
        str url
    }

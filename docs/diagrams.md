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
    CATEGORY |o--o{ PAYMENT : linked_to
    CATEGORY }o--|| ACTIVITY : linked_to
    REQUISITION }o--|| USER : created_by
    BANK_ACCOUNT }o--|| REQUISITION : linked_to
    PAYMENT }o--o| BANK_ACCOUNT : linked_to
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
# Entity-Relationship Diagram

```mermaid
erDiagram
    NN_FUND_ACCOUNT   ||--o{ NN_INCOMING_FUND   : receives
    NN_FUND_ACCOUNT   ||--o{ NN_FUND_ALLOCATION : "source of"
    NN_FUND_ACCOUNT   ||--o{ NN_FUND_MOVEMENT   : "account lines"

    NN_PROJECT        ||--o{ NN_FUND_ALLOCATION  : "target (xor head)"
    NN_PROJECT        ||--o{ NN_FUND_REQUISITION : "drawn from"
    NN_EXPENSE_HEAD   ||--o{ NN_FUND_ALLOCATION  : "target (xor project)"
    NN_EXPENSE_HEAD   ||--o{ NN_FUND_REQUISITION : "drawn from"

    NN_FUND_REQUISITION ||--o{ NN_FUND_BILL      : "billed by"
    NN_FUND_REQUISITION ||--o{ NN_APPROVAL_LINE  : "history"
    NN_FUND_ALLOCATION  ||--o{ NN_APPROVAL_LINE  : "history"
    NN_FUND_TRANSFER    ||--o{ NN_APPROVAL_LINE  : "history"

    NN_FUND_ALLOCATION  ||--o{ NN_FUND_MOVEMENT  : posts
    NN_FUND_REQUISITION ||--o{ NN_FUND_MOVEMENT  : posts
    NN_FUND_BILL        ||--o{ NN_FUND_MOVEMENT  : posts
    NN_FUND_TRANSFER    ||--o{ NN_FUND_MOVEMENT  : posts
    NN_INCOMING_FUND    ||--o{ NN_FUND_MOVEMENT  : posts

    NN_FUND_ACCOUNT {
        char   name
        selection account_type "bank/cash/other"
        many2one company_id
        monetary received        "computed"
        monetary unassigned      "computed"
        monetary on_hold         "computed"
        monetary assigned        "computed"
    }
    NN_INCOMING_FUND {
        char     name
        many2one fund_account_id
        date     date
        monetary amount
        char     transaction_reference
        char     sender
        text     description
        binary   attachment
        selection state "draft/confirmed"
    }
    NN_FUND_MOVEMENT {
        datetime date
        selection move_type "incoming/hold/release/assign/spend/transfer_in/transfer_out/reverse"
        monetary amount
        reference from_bucket
        reference to_bucket
        char     origin_model
        integer  origin_id
        selection state
    }
    NN_PROJECT {
        char name
        monetary allocated         "computed"
        monetary available         "computed"
        monetary requisition_hold  "computed"
        monetary transfer_hold     "computed"
        monetary approved_unspent  "computed"
        monetary spent             "computed"
        monetary transfer_in       "computed"
        monetary transfer_out      "computed"
    }
    NN_EXPENSE_HEAD {
        char name
        monetary allocated  "computed"
        monetary available  "computed"
        monetary spent      "computed"
    }
    NN_FUND_ALLOCATION {
        char     name "sequence"
        many2one fund_account_id
        many2one project_id   "xor head"
        many2one expense_head_id "xor project"
        monetary amount
        text     purpose
        selection state
    }
    NN_FUND_REQUISITION {
        char     name "sequence"
        many2one project_id  "xor head"
        many2one expense_head_id
        monetary amount
        monetary remaining_billable "computed"
        selection state "+closed"
    }
    NN_FUND_BILL {
        char     name "sequence"
        many2one requisition_id
        monetary amount
        selection state "draft/posted/cancelled"
    }
    NN_FUND_TRANSFER {
        char     name "sequence"
        reference source_bucket
        reference dest_bucket
        monetary amount
        selection state
    }
    NN_APPROVAL_LINE {
        many2one approver_id
        datetime decision_date
        selection level "gm/md/finance"
        selection result "approved/rejected"
        text comment
    }
```

> `*_bucket` fields are `reference` (or a pair of nullable many2ones `project_id`/`expense_head_id`
> with a XOR constraint) so a single field can point at either a project or an expense head.
> Decide one style and keep it consistent — see `models-spec.md`.

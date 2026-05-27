"""GraphQL query definitions for the accounting API.

These queries mirror the data shape returned by MockDataProvider.
When connecting to your real GraphQL API, update these queries
to match your actual schema.

NOTE: The local mock server (graphql_server.py) uses strawberry which
auto-converts Python snake_case to camelCase. These queries use camelCase
field names to match. Your production API may use different field names.
"""

GET_BUSINESS_INFO = """
query GetBusinessInfo($businessId: String!, $taxYear: Int!) {
  business(id: $businessId, taxYear: $taxYear) {
    id
    name
    accountingMethod
    jurisdiction
    fiscalYearEnd
    businessType
    address {
      city
      province
      postalCode
      country
    }
    gstHstNumber
    taxYear
  }
}
"""

GET_INCOME = """
query GetIncome($businessId: String!, $taxYear: Int!) {
  profitAndLoss(businessId: $businessId, taxYear: $taxYear, type: "CREDIT") {
    businessId
    taxYear
    accounts {
      name
      type
      amount
    }
    totalRevenue
  }
}
"""

GET_EXPENSES = """
query GetExpenses($businessId: String!, $taxYear: Int!) {
  profitAndLoss(businessId: $businessId, taxYear: $taxYear, type: "DEBIT") {
    businessId
    taxYear
    accounts {
      name
      type
      amount
    }
    totalExpenses
  }
}
"""

GET_ASSETS = """
query GetAssets($businessId: String!, $taxYear: Int!) {
  taxAccounts(businessId: $businessId, taxYear: $taxYear) {
    businessId
    taxYear
    hstCollected
    hstPaid
    netHst
    province
    rate
    rateType
    description
  }
}
"""

GET_TAX_RULES = """
query GetTaxRules($jurisdiction: String!, $taxYear: Int!) {
  taxRules(jurisdiction: $jurisdiction, taxYear: $taxYear) {
    federal {
      taxYear
      brackets {
        min
        max
        rate
      }
      basicPersonalAmount
    }
    provincial {
      jurisdiction
      name
      taxYear
      brackets {
        min
        max
        rate
      }
      basicPersonalAmount
    }
    cpp {
      rate
      maxPensionableEarnings
      basicExemption
      maxContribution
      maxSelfEmployedContribution
    }
    ei {
      rate
      maxInsurableEarnings
      maxPremium
      maxSelfEmployedPremium
    }
  }
}
"""

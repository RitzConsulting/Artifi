#!/usr/bin/env python3
"""
InsureMO Rate Tool - Commercial Insurance Premium Rating
Blueprint-Compliant Tool with Fixed Retry Compatibility

Version: 2.2.0 - Fixed urllib3 compatibility issues
"""

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import requests with proper error handling
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("\nError: requests package is required. Install with: pip install requests")
    sys.exit(1)


class InsuremoRateTool:
    """
    Blueprint-Compliant InsureMO Rating API Client
    
    Provides simplified premium rating for commercial insurance policies.
    """
    
    # Tool metadata
    name = "InsuremoRateTool"
    description = "Commercial insurance premium rating via InsureMO API"
    version = "2.2.0"
    
    # API endpoints
    ENDPOINTS = {
        "create": "/api/ebaogi/api-orchestration/v1/flow/easypa_createOrSave",
        "calculate": "/api/ebaogi/api-orchestration/v1/flow/easypa_calculate"
    }
    
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1
    
    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the InsureMO Rate Tool."""
        self.api_token = api_token or os.getenv("INSUREMO_API_TOKEN")
        self.base_url = base_url or os.getenv("INSUREMO_BASE_URL")
        
        if not self.api_token:
            raise ValueError("API token required. Provide as parameter or set INSUREMO_API_TOKEN")
        if not self.base_url:
            raise ValueError("Base URL required. Provide as parameter or set INSUREMO_BASE_URL")
        
        self.session = self._create_session()
        logger.info(f"InsureMO Rate Tool initialized for {self.base_url}")
    
    def _create_session(self):
        """Create a requests session with retry logic (compatible with all urllib3 versions)."""
        session = requests.Session()
        
        # Create retry strategy with compatibility for both old and new urllib3
        retry_kwargs = {
            'total': self.MAX_RETRIES,
            'status_forcelist': [429, 500, 502, 503, 504],
            'backoff_factor': self.BACKOFF_FACTOR
        }
        
        # Try new parameter name first (urllib3 >= 1.26)
        try:
            retry_kwargs['allowed_methods'] = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            retry_strategy = Retry(**retry_kwargs)
        except TypeError:
            # Fall back to old parameter name (urllib3 < 1.26)
            del retry_kwargs['allowed_methods']
            retry_kwargs['method_whitelist'] = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
            retry_strategy = Retry(**retry_kwargs)
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{self.name}/{self.version}"
        })
        
        return session
    
    def _get_default_dates(self) -> Dict[str, str]:
        """Get default dates for policy."""
        today = datetime.now()
        return {
            "proposalDate": today.strftime("%Y-%m-%d"),
            "effectiveDate": today.strftime("%Y-%m-%d"),
            "expiryDate": (today + timedelta(days=365)).strftime("%Y-%m-%d"),
            "dateStarted": (today - timedelta(days=730)).strftime("%Y-%m-%d"),
            "dateOfBirth": (today - timedelta(days=730)).strftime("%Y-%m-%d")
        }
    
    def _build_policy_payload(self, **kwargs) -> Dict[str, Any]:
        """Build the complete policy payload with defaults."""
        dates = self._get_default_dates()
        
        # Build base payload with all defaults
        payload = {
            "ProductCode": "X_CO_US_USCGLPP8",
            "ProductVersion": "20240801_V01",
            "OrgCode": "10001",
            "AgentCode": "PTY10000039468001",
            "PremiumCurrencyCode": "USD",
            "BookCurrencyCode": "USD",
            "PremiumBookExchangeRate": 1,
            "LocalCurrencyCode": "USD",
            "PremiumLocalExchangeRate": 1,
            "ProposalDate": dates["proposalDate"],
            "EffectiveDate": dates["effectiveDate"],
            "ExpiryDate": dates["expiryDate"],
            
            # Customer information
            "PolicyCustomerList": [{
                "CustomerName": kwargs.get("customerName", ""),
                "CustomerNo": kwargs.get("customerNo", "CO00000001"),
                "DateOfBirth": dates["dateOfBirth"],
                "IdNo": kwargs.get("idNo", "01010101"),
                "IdType": "4",
                "IsOrgParty": "N",
                "PolicyStatus": 2,
                "PostCode": kwargs.get("postCode", kwargs.get("zipCode", "")),
                "CustomerType": "OrgCustomer",
                "State": kwargs.get("state", ""),
                "IsPolicyHolder": "Y"
            }],
            
            # Payment information
            "PolicyPaymentInfoList": [{
                "PayModeCode": 100,
                "IsInstallment": "N",
                "InstallmentType": "10",
                "BillingType": "1"
            }],
            
            # Policy Line of Business
            "PolicyLobList": [{
                "XCGLIncluded": "Yes",
                "XCFIncluded": "Yes",
                "XEachOccurrenceLimit": kwargs.get("eachOccurrenceLimit", "1,000,000 CSL"),
                "XGeneralAggregateLimit": kwargs.get("generalAggregateLimit", "2,000,000 CSL"),
                "XPersonalAdvertisingInjuryLimit": "1000000",
                "XDamageToRentedPremisesLimit": "100000",
                "XMedicalExpenseLimit": "5000",
                "XProdsCompldOpsAggregateLimit": kwargs.get("generalAggregateLimit", "2,000,000 CSL"),
                "XBIDeductibles": "1,000 Per Occurrence",
                "XPDDeductibles": "1,000 Per Occurrence",
                
                # Risk questions - all defaulted to "No"
                "XMedicalFacilitiesOrProfessionals": "No",
                "XExposureToRadioactiveMaterials": "No",
                "XOperationsInvolvingHazardousMaterial": "No",
                "XOperationsSoldAcquiredDiscontinued5Years": "No",
                "XMachineryEquipmentLoanedOrRented": "No",
                "XWatercraftDocksFloatsOwnedHiredLeased": "No",
                "XParkingFacilitiesOwnedRented": "No",
                "XFeeChargedForParking": "No",
                "XRecreationFacilitiesProvided": "No",
                "XSwimmingPoolOnPremises": "No",
                "XSportingSocialEventsSponsored": "No",
                "XStructuralAlterationsContemplated": "No",
                "XDemolitionExposureContemplated": "No",
                "XActiveInJointVentures": "No",
                "XLeaseEmployeesToFromOtherEmployers": "No",
                "XLaborInterchangeWithOtherBusinesses": "No",
                "XDayCareFacilitiesOperatedControlled": "No",
                "XCrimesOccurredOnPremisesLast3Years": "No",
                "XWrittenSafetySecurityPolicyInEffect": "No",
                "XPromotionalLiteratureSafetySecurity": "No",
                "XLossHistorySumaryHeader": "No",
                "XLossHistoryYears": 3,
                
                # Premium fields
                "XCalculatedTotalPremium": 0,
                "XPremium": 0,
                "XPolicyTermPremium": 0,
                "XFinalPremium": 0,
                
                # Business information
                "XSIC": "5461",
                "XNAICSCode": kwargs.get("naicsCode", "311811"),
                "XNAICSDefinition": kwargs.get("naicsDefinition", "Retail Bakeries"),
                "XLegalStructure": kwargs.get("legalStructure", "LLC"),
                "XLLCNumOfMembersManagers": 2,
                "XBusinessType": kwargs.get("businessType", "Retail"),
                "XDateStarted": dates["dateStarted"],
                "XPrimaryOperations": "",
                "XRetailPct": 100,
                
                # Location and risk information
                "PolicyRiskList": [{
                    "XUnitNumber": 1,
                    "XAnyAreaLeasedToOthers": "No",
                    "XProtectionClass": "5",
                    "XGLPremium": 0,
                    "XCFPremium": 0,
                    "XCalculatedTotalPremium": 0,
                    "XPremium": 0,
                    "XPolicyTermPremium": 0,
                    "XAddress1": kwargs.get("address1", ""),
                    "XCity": kwargs.get("city", ""),
                    "XAddress2": "",
                    "XCounty": "",
                    "XState": kwargs.get("state", ""),
                    "XZipCode": kwargs.get("zipCode", ""),
                    "XCityLimits": "Inside",
                    "XLocInterest": "Owner",
                    "XFullTimeEmpl": int(kwargs.get("fullTimeEmpl", 5)),
                    "XPartTimeEmpl": int(kwargs.get("partTimeEmpl", 0)),
                    
                    # Coverage details
                    "PolicyRiskList": [
                        # GL Classification
                        {
                            "XClassCode": "10100",
                            "XClassDescription": "Bakeries",
                            "PolicyCoverageList": [
                                {
                                    "XInstallServiceDemonstrateProducts": "No",
                                    "XForeignProductsSoldDistributedUsed": "No",
                                    "XResearchDevelopmentNewProducts": "No",
                                    "XGuaranteesWarrantiesHoldHarmless": "No",
                                    "XProductsAircraftSpaceIndustry": "No",
                                    "XProductsRecalledDiscontinuedChanged": "No",
                                    "XProductsOthersSoldRepackaged": "No",
                                    "XProductsUnderLabelOfOthers": "No",
                                    "XVendorsCoverageRequired": "No",
                                    "XNamedInsuredSellToOtherInsureds": "No",
                                    "XProdsCompldOpsPremiumBasis": "Gross Sales",
                                    "XProdsCompldOpsCovExposure": 1000000,
                                    "XProdsCompldOpsRate": 0.12,
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCLASSIFICATIONPRODSCOMPLDOPSCOVERAGE"
                                },
                                {
                                    "XPremOpsPremiumBasis": "Gross Sales",
                                    "XPremOpsExposure": 1000000,
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCLASSIFICATIONPREMOPSCOVERAGE"
                                }
                            ],
                            "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONGLCLASSIFICATION"
                        },
                        # Building Coverage
                        {
                            "XUnitNumber": 1,
                            "XDesignatedAsHistoricalLandmark": "No",
                            "XBldgImpWiring": "No",
                            "XBldgImpPlumbing": "No",
                            "XBldgImpRoofing": "No",
                            "XBldgImpHeating": "No",
                            "XWindClass": "NA",
                            "XSolidFuelHeater": "No",
                            "XBurglarAlarmCentralStation": "No",
                            "XBurglarAlarmLocalGong": "No",
                            "XGuardsClockFreq": "Hourly",
                            "XFireAlarmCentralStation": "No",
                            "XFireAlarmLocalGong": "No",
                            "XBldgDescription": "Commercial Building",
                            "XOpenSides": 0,
                            "XConstructionType": "FireResistive",
                            "XNumberOfStories": 1,
                            "XYearBuilt": 2010,
                            "XTotalArea": 5000,
                            "XBCEG": 2,
                            "PolicyCoverageList": [
                                {
                                    "XCoverageOnPolicyIndicator": 1,
                                    "XBldgCovCoins": "80",
                                    "XBldgCovValuation": "A",
                                    "XBldgCovCauseOfLoss": "Special",
                                    "XBldgCovInflationGuard": 5,
                                    "XBldgCovDeductible": 500,
                                    "XBldgCovLimit": int(kwargs.get("buildingLimit", 500000)),
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBUILDINGCOVERAGE"
                                },
                                {
                                    "XCoverageOnPolicyIndicator": 1,
                                    "XPersonalProperty": "Yes",
                                    "XPropertyOfOthers": "Yes",
                                    "XStock": "No",
                                    "XFixturesFurnitures": "No",
                                    "XMachineryEquipment": "No",
                                    "XBPPCovCoins": "80",
                                    "XBPPCovValuation": "A",
                                    "XBPPCovCauseOfLoss": "Special",
                                    "XBPPCovInflationGuard": 5,
                                    "XBPPCovDeductible": 500,
                                    "XBPPCovLimit": int(kwargs.get("bppLimit", 100000)),
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBPPCOVERAGE"
                                },
                                {
                                    "XCoverageOnPolicyIndicator": 1,
                                    "XBICCoverage": "BusinessIncomeWithExtraExpense",
                                    "XBICCovCoins": "80",
                                    "XBICCovCauseOfLoss": "Special",
                                    "XWaitingPeriodDays": 3,
                                    "XBICOrdinaryPayrollExcluded": "No",
                                    "XBICOrdinaryPayrollLimitation": "90Days",
                                    "XBICExtendedPeriodOfIndemnity": "No",
                                    "XBICMonthlyPeriodOfIndemnity": "No",
                                    "XBICMaximumPeriodOfIndemnity": "No",
                                    "XBICPowerHeatDed": "No",
                                    "XBICEMediaRec": "No",
                                    "XBIEOrdOrLaw": "No",
                                    "XBICCivilAuth": "No",
                                    "XBICOffPremSrvInt": "No",
                                    "XBICDependProp": "No",
                                    "XBICCovLimit": 200000,
                                    "XBICTypeOfBusiness": "NonManufacturing",
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGBIC"
                                },
                                {
                                    "XCoverageOnPolicyIndicator": 0,
                                    "XSCDeductible": 500,
                                    "XSCRefrigMaintAgreement": "No",
                                    "XSCBreakdownOrContamination": "No",
                                    "XSCPowerOutage": "No",
                                    "XSCSellingPrice": "No",
                                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDINGSPOILAGECOVERAGE"
                                }
                            ],
                            "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATIONCFBUILDING"
                        }
                    ],
                    "ProductElementCode": "MASTERGENLIA01BASELAYERLOCATION"
                }],
                "ProductCode": "X_CO_US_USCGLPP8",
                "ProductElementCode": "X_CO_US_USCGLPP8"
            }]
        }
        
        return payload
    
    @contextmanager
    def _api_call_context(self, action: str):
        """Context manager for API calls with timing and error handling."""
        start_time = time.time()
        try:
            logger.info(f"Starting API call: {action}")
            yield
        except Exception as e:
            logger.error(f"API call failed: {action} - {str(e)}")
            raise
        finally:
            elapsed = time.time() - start_time
            logger.info(f"API call completed: {action} in {elapsed:.2f}s")
    
    def _extract_premium_breakdown(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed premium breakdown from policy data."""
        breakdown = {
            "totalPremium": policy_data.get("TotalPremium", 0),
            "grossPremium": policy_data.get("GrossPremium", 0),
            "glPremium": 0,
            "propertyPremium": 0,
            "buildingPremium": 0,
            "bppPremium": 0,
            "biPremium": 0
        }
        
        # Extract component premiums if available
        try:
            lob_list = policy_data.get("PolicyLobList", [])
            if lob_list:
                risk_list = lob_list[0].get("PolicyRiskList", [])
                if risk_list:
                    location = risk_list[0]
                    breakdown["glPremium"] = location.get("XGLPremium", 0)
                    breakdown["propertyPremium"] = location.get("XCFPremium", 0)
        except Exception as e:
            logger.warning(f"Could not extract detailed premium breakdown: {str(e)}")
        
        return breakdown
    
    def get_quote(self, **kwargs) -> Dict[str, Any]:
        """
        Get insurance quote with premium calculation.
        
        Args:
            **kwargs: Business information for rating
            
        Returns:
            Dictionary with rating results
        """
        try:
            # Step 1: Create policy with provided data
            with self._api_call_context("create"):
                payload = self._build_policy_payload(**kwargs)
                
                url = f"{self.base_url}{self.ENDPOINTS['create']}"
                response = self.session.post(url, json=payload, timeout=self.DEFAULT_TIMEOUT)
                
                if response.status_code != 200:
                    raise Exception(f"Create API returned status {response.status_code}: {response.text}")
                
                created_data = response.json()
                proposal_no = created_data.get("ProposalNo")
                
                if not proposal_no:
                    raise Exception("No proposal number returned from create API")
                
                logger.info(f"Policy created with proposal number: {proposal_no}")
            
            # Step 2: Calculate premium
            with self._api_call_context("calculate"):
                url = f"{self.base_url}{self.ENDPOINTS['calculate']}"
                response = self.session.post(url, json=created_data, timeout=self.DEFAULT_TIMEOUT)
                
                if response.status_code != 200:
                    raise Exception(f"Calculate API returned status {response.status_code}: {response.text}")
                
                calculated_data = response.json()
                
                logger.info(f"Premium calculated: ${calculated_data.get('TotalPremium', 0)}")
            
            # Extract premium breakdown
            premium_breakdown = self._extract_premium_breakdown(calculated_data)
            
            # Build successful response
            return {
                "success": True,
                "proposalNo": calculated_data.get("ProposalNo"),
                "policyId": calculated_data.get("PolicyId"),
                "totalPremium": calculated_data.get("TotalPremium", 0),
                "grossPremium": calculated_data.get("GrossPremium", 0),
                "commission": calculated_data.get("Commission", 0),
                "commissionRate": calculated_data.get("CommissionRate", 0),
                "glPremium": premium_breakdown["glPremium"],
                "propertyPremium": premium_breakdown["propertyPremium"],
                "effectiveDate": calculated_data.get("EffectiveDate"),
                "expiryDate": calculated_data.get("ExpiryDate"),
                "premiumBreakdown": premium_breakdown
            }
            
        except Exception as e:
            logger.error(f"Rate tool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "errorDetails": {
                    "type": type(e).__name__,
                    "message": str(e)
                }
            }


def execute_tool(**kwargs) -> Dict[str, Any]:
    """
    Standard entry point for the tool.
    
    Args:
        **kwargs: Tool input parameters
        
    Returns:
        Dict containing rating results
    """
    try:
        # Extract API credentials from kwargs or environment
        api_token = kwargs.pop("api_token", None) or os.getenv("INSUREMO_API_TOKEN")
        base_url = kwargs.pop("base_url", None) or os.getenv("INSUREMO_BASE_URL")
        
        # Validate credentials
        if not api_token:
            return {
                "success": False,
                "error": "API token required. Provide as 'api_token' parameter or set INSUREMO_API_TOKEN environment variable"
            }
        
        if not base_url:
            return {
                "success": False,
                "error": "Base URL required. Provide as 'base_url' parameter or set INSUREMO_BASE_URL environment variable"
            }
        
        # Create tool instance
        tool = InsuremoRateTool(api_token=api_token, base_url=base_url)
        
        # Execute rating
        return tool.get_quote(**kwargs)
        
    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "errorType": type(e).__name__
        }


def main():
    """Main function for testing."""
    print("\n" + "="*80)
    print(" InsureMO Rate Tool - Commercial Insurance Premium Calculator")
    print("="*80)
    print(" Version: 2.2.0 | Blueprint-Compliant | Fixed Compatibility")
    print("-"*80)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Small Retail Bakery",
            "data": {
                "customerName": "Sweet Dreams Bakery LLC",
                "address1": "123 Main Street",
                "city": "Houston",
                "state": "TX",
                "zipCode": "77001",
                "businessType": "Retail",
                "naicsCode": "311811",
                "naicsDefinition": "Retail Bakeries",
                "fullTimeEmpl": 5,
                "partTimeEmpl": 2,
                "buildingLimit": 500000,
                "bppLimit": 100000
            }
        },
        {
            "name": "Manufacturing Facility",
            "data": {
                "customerName": "TechParts Manufacturing Inc",
                "address1": "456 Industrial Blvd",
                "city": "Dallas",
                "state": "TX",
                "zipCode": "75201",
                "businessType": "Manufacturing",
                "naicsCode": "333316",
                "naicsDefinition": "Photographic Equipment Manufacturing",
                "fullTimeEmpl": 25,
                "partTimeEmpl": 5,
                "buildingLimit": 1500000,
                "bppLimit": 800000,
                "eachOccurrenceLimit": "2,000,000 CSL",
                "generalAggregateLimit": "4,000,000 CSL"
            }
        }
    ]
    
    # Check and set environment variables if not present
    if not os.getenv("INSUREMO_API_TOKEN"):
        print("\n⚠ Warning: INSUREMO_API_TOKEN not set in environment")
        print("  Setting default token for testing...")
        os.environ["INSUREMO_API_TOKEN"] = "MOATnRGmthYVAX1Dcrcve-WV8PEa0nds"
    
    if not os.getenv("INSUREMO_BASE_URL"):
        print("⚠ Warning: INSUREMO_BASE_URL not set in environment")
        print("  Setting default URL for testing...")
        os.environ["INSUREMO_BASE_URL"] = "https://ebaogi-gi-sandbox-am.insuremo.com"
    
    # Run test scenarios
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f" Test Scenario {i}: {scenario['name']}")
        print(f"{'='*80}")
        
        test_data = scenario['data']
        print(f"\nBusiness: {test_data['customerName']}")
        print(f"Location: {test_data['address1']}, {test_data['city']}, {test_data['state']} {test_data['zipCode']}")
        print(f"Type: {test_data['businessType']}")
        print(f"Employees: {test_data['fullTimeEmpl']} FT, {test_data.get('partTimeEmpl', 0)} PT")
        print(f"Building Limit: ${test_data.get('buildingLimit', 500000):,}")
        print(f"BPP Limit: ${test_data.get('bppLimit', 100000):,}")
        
        print("\n" + "-"*40)
        print(" Executing Rating...")
        print("-"*40)
        
        try:
            # Execute the tool
            result = execute_tool(**test_data)
            
            if result["success"]:
                print("\n✅ Rating Successful!")
                print(f"\n📋 Proposal Number: {result.get('proposalNo')}")
                
                print(f"\n💰 Premium Summary:")
                print(f"   Total Premium:    ${result.get('totalPremium', 0):>12,.2f}")
                print(f"   GL Premium:       ${result.get('glPremium', 0):>12,.2f}")
                print(f"   Property Premium: ${result.get('propertyPremium', 0):>12,.2f}")
                print(f"   Commission:       ${result.get('commission', 0):>12,.2f} ({result.get('commissionRate', 0)*100:.1f}%)")
                
                print(f"\n📅 Policy Term:")
                print(f"   Effective Date: {result.get('effectiveDate')}")
                print(f"   Expiry Date:    {result.get('expiryDate')}")
                
                # Save result to file
                filename = f"quote_{i}_{test_data['customerName'].replace(' ', '_').replace('.', '')}.json"
                with open(filename, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n💾 Results saved to: {filename}")
                
            else:
                print(f"\n❌ Rating Failed:")
                print(f"   Error Type: {result.get('errorType')}")
                print(f"   Error: {result.get('error')}")
                
        except Exception as e:
            print(f"\n❌ Test failed with exception:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Brief pause between scenarios
        if i < len(test_scenarios):
            time.sleep(2)
    
    print("\n" + "="*80)
    print(" Testing Complete")
    print("="*80)


if __name__ == "__main__":
    main()
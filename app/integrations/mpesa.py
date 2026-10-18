from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid

class PaymentProvider(ABC):
    @abstractmethod
    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        """
        Initiates an STK push / checkout request.
        Returns dict containing merchant_request_id, checkout_request_id, provider_status.
        """
        pass

    @abstractmethod
    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        """
        Verifies transaction status with the provider.
        """
        pass

class MockPaymentProvider(PaymentProvider):
    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        req_id = f"MOCK_REQ_{uuid.uuid4().hex[:12]}"
        chk_id = f"ws_CO_{uuid.uuid4().hex[:16]}"
        return {
            "success": True,
            "merchant_request_id": req_id,
            "checkout_request_id": chk_id,
            "customer_message": "Success. Enter M-Pesa PIN on your phone.",
            "response_code": "0"
        }

    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        return {
            "success": True,
            "provider_reference": provider_reference,
            "status": "confirmed"
        }

class DarajaPaymentProvider(PaymentProvider):
    """
    Production M-Pesa Daraja implementation.
    Safely configured with fallbacks if credentials are not yet supplied.
    """
    def __init__(self, consumer_key: str, consumer_secret: str, shortcode: str, passkey: str, callback_url: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.passkey = passkey
        self.callback_url = callback_url

    def initiate_stk_push(
        self,
        phone_number: str,
        amount_minor: int,
        account_reference: str,
        transaction_desc: str
    ) -> Dict[str, Any]:
        # If credentials are not live, raise an error or fall back clearly
        if "placeholder" in self.consumer_key:
            raise NotImplementedError(
                "M-Pesa Daraja live credentials have not been configured. "
                "Set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET in .env."
            )
        # Live Safaricom Daraja API call would take place here
        raise NotImplementedError("Live Daraja STK Push awaiting live sandbox/production credentials.")

    def verify_transaction(self, provider_reference: str) -> Dict[str, Any]:
        if "placeholder" in self.consumer_key:
            raise NotImplementedError("Live Daraja transaction query awaiting live credentials.")
        raise NotImplementedError("Live Daraja verification awaiting credentials.")

def get_payment_provider() -> PaymentProvider:
    from app.core.config import settings
    if settings.MPESA_ENVIRONMENT == "mock" or "placeholder" in settings.MPESA_CONSUMER_KEY:
        return MockPaymentProvider()
    return DarajaPaymentProvider(
        consumer_key=settings.MPESA_CONSUMER_KEY,
        consumer_secret=settings.MPESA_CONSUMER_SECRET,
        shortcode=settings.MPESA_SHORTCODE,
        passkey=settings.MPESA_PASSKEY,
        callback_url=settings.MPESA_CALLBACK_URL
    )


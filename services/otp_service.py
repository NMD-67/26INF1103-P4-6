from repositories.otp_repo import OTPRepo
from results.result import Result
from results.error import Error
from results.success import Success
from services.user_service import UserService
from src.email import send_email
import random


class OTPService:
    def __init__(self, otp_repo: OTPRepo):
        self.otp_repo = otp_repo

    async def send_otp(self, student_id: str) -> Result:
        otp = random.randrange(1, 9999)
        upload_otp_result = self.otp_repo.create_otp(student_id, otp)
        if upload_otp_result is None:
            return Error("An error occured when creating OTP")

        email_address = f"{student_id}@sit.singaporetech.edu.sg"
        email_response = await send_email(
            to_email=email_address,
            subject="Your OTP for Login",
            html_content=f"Your OTP is {otp}",
        )

        if email_response is None or email_response == 500:
            return Error("An error occured when sending email")
        return Success("OTP email has been sent!")

    def verify_otp(
        self, student_id: str, otp: str, user_service: UserService
    ) -> Result:
        get_otp_result = self.otp_repo.get_otp(student_id)
        if get_otp_result is None:
            return Error("OTP invalid")
        if str(get_otp_result) != otp:
            return Error("OTP Mismatch")

        self.otp_repo.delete_otp(student_id)
        add_user_result = user_service.login_user(student_id)
        if not add_user_result.success:
            return add_user_result
        return Success("OTP Verified")

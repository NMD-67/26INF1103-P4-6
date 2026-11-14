from repositories.otp_repo import OTPRepo
from results.result import Result
from results.error import Error
from results.success import Success
from services.user_service import UserService
from src.email_sender import EmailSender
import secrets


class OTPService:
    def __init__(self, otp_repo: OTPRepo, email_sender=None):
        self.otp_repo = otp_repo
        self._email_sender = email_sender if email_sender is not None else EmailSender()

    async def send_otp(self, student_id: str) -> Result:
        otp = secrets.randbelow(9000) + 1000
        upload_otp_result = self.otp_repo.create_otp(student_id, otp)
        if not upload_otp_result:
            return Error("An error occured when creating OTP")

        email_address = f"{student_id}@sit.singaporetech.edu.sg"
        email_response = await self._email_sender.send(
            to_email=email_address,
            subject="Your OTP for Login",
            html_content=f"Your OTP is {otp}",
        )

        if email_response != 200:
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

        consumed = self.otp_repo.delete_otp(student_id, expected_otp=get_otp_result)
        if not consumed:
            return Error("OTP expired or already used. Please request a new code.")
        add_user_result = user_service.login_user(student_id)
        if not add_user_result.success:
            return add_user_result
        return Success("OTP Verified")

from __future__ import annotations

import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def _init_resend() -> None:
    resend.api_key = settings.RESEND_API_KEY


def send_email(to: str, subject: str, html_body: str) -> str | None:
    """Send an email via Resend. Returns provider message ID or None on failure."""
    _init_resend()

    params: resend.Emails.SendParams = {
        "from": settings.EMAIL_FROM or "모아오더 <noreply@moaorder.com>",
        "to": [to],
        "subject": subject,
        "html": html_body,
    }
    if settings.EMAIL_REPLY_TO:
        params["reply_to"] = settings.EMAIL_REPLY_TO

    email = resend.Emails.send(params)
    return email.get("id")


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

def _base_template(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family:sans-serif;color:#222;max-width:600px;margin:auto;padding:24px">
  <h2 style="color:#4f46e5">{title}</h2>
  {body_html}
  <hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb"/>
  <p style="font-size:12px;color:#9ca3af">모아오더 | 공동구매 플랫폼</p>
</body>
</html>"""


def render_order_confirmed(product_name: str, quantity: int, amount: int) -> str:
    body = f"""
    <p>주문이 확정되었습니다.</p>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:8px;border:1px solid #e5e7eb">상품명</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{product_name}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">수량</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{quantity}개</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">결제금액</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{amount:,}원</td></tr>
    </table>
    <p>상품 준비가 완료되면 안내드리겠습니다.</p>
    """
    return _base_template("주문이 확정됐어요", body)


def render_order_cancelled(product_name: str, reason: str, refund_amount: int) -> str:
    body = f"""
    <p>주문이 취소되었습니다.</p>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:8px;border:1px solid #e5e7eb">상품명</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{product_name}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">취소 사유</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{reason}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">환불 예정금액</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{refund_amount:,}원</td></tr>
    </table>
    <p>환불은 영업일 기준 3~5일 이내 처리됩니다.</p>
    """
    return _base_template("주문이 취소되었습니다", body)


def render_pickup_ready(product_name: str, quantity: int) -> str:
    body = f"""
    <p>주문하신 상품을 수령할 수 있습니다.</p>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:8px;border:1px solid #e5e7eb">상품명</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{product_name}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">수량</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{quantity}개</td></tr>
    </table>
    <p>판매처에 방문하여 수령해 주세요.</p>
    """
    return _base_template("상품 수령 가능 안내", body)


def render_cancel_approved(product_name: str, refund_amount: int) -> str:
    body = f"""
    <p>취소 요청이 승인되었습니다.</p>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:8px;border:1px solid #e5e7eb">상품명</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{product_name}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">환불 예정금액</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{refund_amount:,}원</td></tr>
    </table>
    """
    return _base_template("취소 요청 승인", body)


def render_cancel_rejected(product_name: str, reason: str) -> str:
    body = f"""
    <p>취소 요청이 거절되었습니다.</p>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:8px;border:1px solid #e5e7eb">상품명</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{product_name}</td></tr>
      <tr><td style="padding:8px;border:1px solid #e5e7eb">거절 사유</td>
          <td style="padding:8px;border:1px solid #e5e7eb">{reason}</td></tr>
    </table>
    """
    return _base_template("취소 요청 거절", body)


# ---------------------------------------------------------------------------
# Auth email templates & senders
# ---------------------------------------------------------------------------

BRAND_COLOR = "#EC4445"


def _auth_base_template(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family:sans-serif;color:#222;max-width:600px;margin:auto;padding:24px">
  <h2 style="color:{BRAND_COLOR}">{title}</h2>
  {body_html}
  <hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb"/>
  <p style="font-size:12px;color:#9ca3af">모아오더 | 공동구매 플랫폼</p>
</body>
</html>"""


def send_verification_code_email(to: str, code: str) -> str | None:
    """Send a 6-digit inline-signup verification code."""
    body = f"""
    <p>모아오더 회원가입을 진행해주셔서 감사합니다.</p>
    <p>아래 인증번호를 가입 화면에 입력해주세요.</p>
    <p style="margin:24px 0">
      <span style="display:inline-block;font-size:32px;letter-spacing:8px;font-weight:bold;color:{BRAND_COLOR};
                   border:1px solid #e5e7eb;border-radius:8px;padding:16px 24px;background:#fafafa">
        {code}
      </span>
    </p>
    <p style="font-size:13px;color:#6b7280">인증번호는 5분 동안 유효합니다. 본인이 요청하지 않으셨다면 이 메일을 무시하세요.</p>
    """
    html = _auth_base_template("이메일 인증번호", body)
    return send_email(to, "[모아오더] 인증번호를 입력해주세요", html)


def send_verification_email(to: str, token: str, nickname: str) -> str | None:
    """Send email verification link."""
    verify_url = f"{settings.FRONTEND_URL}/auth/email/verify?token={token}"
    body = f"""
    <p>안녕하세요, {nickname}님!</p>
    <p>아래 버튼을 눌러 이메일 인증을 완료해주세요.</p>
    <p style="margin:24px 0">
      <a href="{verify_url}"
         style="background:{BRAND_COLOR};color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">
        이메일 인증하기
      </a>
    </p>
    <p style="font-size:13px;color:#6b7280">링크는 24시간 후 만료됩니다.</p>
    <p style="font-size:12px;color:#9ca3af;word-break:break-all">
      버튼이 동작하지 않으면 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>{verify_url}
    </p>
    """
    html = _auth_base_template("이메일 인증", body)
    return send_email(to, "[모아오더] 이메일 인증을 완료해주세요", html)


def send_password_reset_email(to: str, token: str, nickname: str) -> str | None:
    """Send password reset link."""
    reset_url = f"{settings.FRONTEND_URL}/auth/email/reset?token={token}"
    body = f"""
    <p>안녕하세요, {nickname}님!</p>
    <p>비밀번호 재설정 요청이 접수되었습니다. 아래 버튼을 눌러 새 비밀번호를 설정하세요.</p>
    <p style="margin:24px 0">
      <a href="{reset_url}"
         style="background:{BRAND_COLOR};color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">
        비밀번호 재설정
      </a>
    </p>
    <p style="font-size:13px;color:#6b7280">링크는 1시간 후 만료됩니다. 본인이 요청하지 않으셨다면 이 메일을 무시하세요.</p>
    <p style="font-size:12px;color:#9ca3af;word-break:break-all">
      버튼이 동작하지 않으면 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>{reset_url}
    </p>
    """
    html = _auth_base_template("비밀번호 재설정", body)
    return send_email(to, "[모아오더] 비밀번호 재설정 링크", html)

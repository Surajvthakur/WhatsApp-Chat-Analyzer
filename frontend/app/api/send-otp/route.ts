import { NextResponse } from "next/server";
import nodemailer from "nodemailer";

export async function POST(req: Request) {
  try {
    const { email, code, secret } = await req.json();

    const expectedSecret = process.env.AUTH_SECRET;
    if (expectedSecret && secret !== expectedSecret) {
      return NextResponse.json({ error: "Unauthorized secret" }, { status: 401 });
    }

    if (!email || !code) {
      return NextResponse.json({ error: "Missing email or code" }, { status: 400 });
    }

    const user = process.env.GMAIL_USER || process.env.MAIL_USERNAME;
    const pass = process.env.GMAIL_PASS || process.env.MAIL_PASSWORD;

    if (!user || !pass) {
      console.warn("GMAIL_USER or GMAIL_PASS environment variables not set on Vercel.");
      return NextResponse.json(
        { error: "Gmail credentials not configured on Vercel" },
        { status: 500 }
      );
    }

    const cleanPass = pass.replace(/["'\s]/g, "");

    const transporter = nodemailer.createTransport({
      host: "smtp.gmail.com",
      port: 465,
      secure: true,
      auth: {
        user: user.trim(),
        pass: cleanPass,
      },
    });

    const html = `
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px; background: #111b21; border-radius: 16px; color: #e9edef;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #25d366; font-size: 22px; margin: 0;">WhatsApp Chat Analyzer</h1>
            <p style="color: #8696a0; font-size: 13px; margin-top: 6px;">Email Verification</p>
        </div>
        <div style="background: #202c33; border-radius: 12px; padding: 28px; text-align: center;">
            <p style="color: #e9edef; font-size: 15px; margin: 0 0 20px;">Your verification code is:</p>
            <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #25d366; padding: 12px 0;">
                ${code}
            </div>
            <p style="color: #8696a0; font-size: 12px; margin-top: 20px;">
                This code expires in <strong style="color: #e9edef;">5 minutes</strong>.
            </p>
        </div>
        <p style="color: #667781; font-size: 11px; text-align: center; margin-top: 20px;">
            If you didn't request this code, you can safely ignore this email.
        </p>
    </div>
    `;

    await transporter.sendMail({
      from: `"WhatsApp Chat Analyzer" <${user}>`,
      to: email,
      subject: "Your Verification Code — WhatsApp Chat Analyzer",
      html,
    });

    console.log(`Successfully sent OTP email to ${email} via Vercel nodemailer`);
    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error("Vercel Email Relay Error:", error);
    return NextResponse.json(
      { error: error.message || "Failed to send email" },
      { status: 500 }
    );
  }
}

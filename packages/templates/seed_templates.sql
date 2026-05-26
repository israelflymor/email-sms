insert into message_templates (id, name, category, body, approved, version)
values
  (gen_random_uuid(), 'otp_code', 'otp', 'Your verification code is {{code}}. It expires in 5 minutes.', true, 1),
  (gen_random_uuid(), 'order_shipped', 'transactional', 'Your order has shipped. Track it here: {{tracking_url}}', true, 1),
  (gen_random_uuid(), 'promo_welcome', 'promotional', 'Welcome! Msg frequency varies. Reply STOP to opt out.', true, 1);

-- Supabase テーブル作成SQL

-- ユーザーテーブル（Supabaseの認証と連携）
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    stripe_customer_id TEXT UNIQUE,
    full_name TEXT,
    phone TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- RLS（行レベルセキュリティ）の設定
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- ユーザー自身のレコードのみアクセス可能なポリシー
CREATE POLICY "ユーザーは自分自身のレコードのみ参照可能" ON public.users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "ユーザーは自分自身のレコードのみ更新可能" ON public.users
  FOR UPDATE USING (auth.uid() = id);

-- 商品/プランテーブル
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_product_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    is_subscription BOOLEAN NOT NULL DEFAULT FALSE,
    interval TEXT CHECK (interval IN ('month', 'year', NULL)),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    features JSONB DEFAULT '{}'
);

-- RLS（行レベルセキュリティ）の設定
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;

-- 全ユーザーが製品を参照可能なポリシー
CREATE POLICY "全ユーザーが製品を参照可能" ON public.products
  FOR SELECT USING (TRUE);

-- 管理者のみ製品を更新・作成・削除可能なポリシー
CREATE POLICY "管理者のみ製品を更新可能" ON public.products
  FOR UPDATE USING (auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE));

CREATE POLICY "管理者のみ製品を作成可能" ON public.products
  FOR INSERT WITH CHECK (auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE));

CREATE POLICY "管理者のみ製品を削除可能" ON public.products
  FOR DELETE USING (auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE));

-- 複合インデックスの作成
CREATE INDEX idx_products_subscription_active ON public.products (is_subscription, is_active);

-- サブスクリプションテーブル
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT NOT NULL,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at TIMESTAMP WITH TIME ZONE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

-- RLS（行レベルセキュリティ）の設定
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- ユーザー自身のサブスクリプションのみ参照可能なポリシー
CREATE POLICY "ユーザーは自分のサブスクリプションのみ参照可能" ON public.subscriptions
  FOR SELECT USING (auth.uid() = user_id);

-- 管理者とシステムのみサブスクリプションを作成・更新可能なポリシー
CREATE POLICY "管理者とシステムのみサブスクリプションを作成可能" ON public.subscriptions
  FOR INSERT WITH CHECK (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

CREATE POLICY "管理者とシステムのみサブスクリプションを更新可能" ON public.subscriptions
  FOR UPDATE USING (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

-- インデックスの作成
CREATE INDEX idx_subscriptions_user_product ON public.subscriptions (user_id, product_id);
CREATE INDEX idx_subscriptions_status_period_end ON public.subscriptions (status, current_period_end);

-- 購入テーブル
CREATE TABLE IF NOT EXISTS public.purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
    stripe_payment_intent_id TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,
    purchased_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

-- RLS（行レベルセキュリティ）の設定
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;

-- ユーザー自身の購入履歴のみ参照可能なポリシー
CREATE POLICY "ユーザーは自分の購入履歴のみ参照可能" ON public.purchases
  FOR SELECT USING (auth.uid() = user_id);

-- 管理者とシステムのみ購入履歴を作成・更新可能なポリシー
CREATE POLICY "管理者とシステムのみ購入履歴を作成可能" ON public.purchases
  FOR INSERT WITH CHECK (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

CREATE POLICY "管理者とシステムのみ購入履歴を更新可能" ON public.purchases
  FOR UPDATE USING (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

-- インデックスの作成
CREATE INDEX idx_purchases_user_product ON public.purchases (user_id, product_id);
CREATE INDEX idx_purchases_status ON public.purchases (status);

-- 支払い履歴テーブル
CREATE TABLE IF NOT EXISTS public.payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE SET NULL,
    purchase_id UUID REFERENCES public.purchases(id) ON DELETE SET NULL,
    stripe_payment_intent_id TEXT,
    stripe_invoice_id TEXT,
    amount INTEGER NOT NULL,
    payment_method TEXT,
    status TEXT NOT NULL,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

-- RLS（行レベルセキュリティ）の設定
ALTER TABLE public.payment_history ENABLE ROW LEVEL SECURITY;

-- ユーザー自身の支払い履歴のみ参照可能なポリシー
CREATE POLICY "ユーザーは自分の支払い履歴のみ参照可能" ON public.payment_history
  FOR SELECT USING (auth.uid() = user_id);

-- 管理者とシステムのみ支払い履歴を作成・更新可能なポリシー
CREATE POLICY "管理者とシステムのみ支払い履歴を作成可能" ON public.payment_history
  FOR INSERT WITH CHECK (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

CREATE POLICY "管理者とシステムのみ支払い履歴を更新可能" ON public.payment_history
  FOR UPDATE USING (
    auth.uid() IN (SELECT id FROM public.users WHERE is_admin = TRUE)
    OR auth.uid() = '00000000-0000-0000-0000-000000000000' -- システムユーザーID
  );

-- インデックスの作成
CREATE INDEX idx_payment_history_user_id ON public.payment_history (user_id);
CREATE INDEX idx_payment_history_subscription_id ON public.payment_history (subscription_id);
CREATE INDEX idx_payment_history_purchase_id ON public.payment_history (purchase_id);
CREATE INDEX idx_payment_history_status ON public.payment_history (status);
CREATE INDEX idx_payment_history_paid_at ON public.payment_history (paid_at);

-- 管理者フラグをユーザーテーブルに追加
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- トリガー関数: 更新日時を自動更新
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 各テーブルに自動更新トリガーを設定
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_products_updated_at
BEFORE UPDATE ON public.products
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at
BEFORE UPDATE ON public.subscriptions
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_purchases_updated_at
BEFORE UPDATE ON public.purchases
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column(); 
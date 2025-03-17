# Supabase データベース設計

## 概要
このドキュメントでは、Stripeを使用したサブスクリプションおよび買い切りプラン決済機能のためのテーブル設計について説明します。

## テーブル構成

### 1. users（ユーザーテーブル）
Supabaseの認証システムと連携するユーザー情報テーブル

| カラム名 | データ型 | 説明 | 制約 |
|---------|---------|------|------|
| id | uuid | ユーザーID | PRIMARY KEY, NOT NULL |
| email | text | メールアドレス | UNIQUE, NOT NULL |
| created_at | timestamp with time zone | 作成日時 | NOT NULL, DEFAULT now() |
| updated_at | timestamp with time zone | 更新日時 | DEFAULT now() |
| stripe_customer_id | text | Stripe顧客ID | UNIQUE |
| full_name | text | 氏名 | |
| phone | text | 電話番号 | |
| is_active | boolean | アクティブ状態 | NOT NULL, DEFAULT true |

### 2. products（商品/プランテーブル）
サブスクリプションと買い切りの両方のプランを管理するテーブル

| カラム名 | データ型 | 説明 | 制約 |
|---------|---------|------|------|
| id | uuid | 商品ID | PRIMARY KEY, NOT NULL |
| stripe_product_id | text | StripeプロダクトID | UNIQUE, NOT NULL |
| name | text | 商品名 | NOT NULL |
| description | text | 商品説明 | |
| price | integer | 価格（円） | NOT NULL |
| is_subscription | boolean | サブスクリプションかどうか | NOT NULL, DEFAULT false |
| interval | text | サブスクの場合の更新間隔（month/year/null） | |
| created_at | timestamp with time zone | 作成日時 | NOT NULL, DEFAULT now() |
| updated_at | timestamp with time zone | 更新日時 | DEFAULT now() |
| is_active | boolean | 有効状態 | NOT NULL, DEFAULT true |
| features | jsonb | 機能一覧 | DEFAULT '{}' |

### 3. subscriptions（サブスクリプションテーブル）
ユーザーのサブスクリプション状態を管理するテーブル

| カラム名 | データ型 | 説明 | 制約 |
|---------|---------|------|------|
| id | uuid | サブスクリプションID | PRIMARY KEY, NOT NULL |
| user_id | uuid | ユーザーID | NOT NULL, REFERENCES users(id) |
| product_id | uuid | 商品ID | NOT NULL, REFERENCES products(id) |
| stripe_subscription_id | text | StripeサブスクリプションID | UNIQUE |
| status | text | ステータス（active, canceled, past_due など） | NOT NULL |
| current_period_start | timestamp with time zone | 現在の期間開始日 | |
| current_period_end | timestamp with time zone | 現在の期間終了日 | |
| cancel_at | timestamp with time zone | キャンセル予定日 | |
| canceled_at | timestamp with time zone | キャンセル日 | |
| created_at | timestamp with time zone | 作成日時 | NOT NULL, DEFAULT now() |
| updated_at | timestamp with time zone | 更新日時 | DEFAULT now() |
| metadata | jsonb | メタデータ | DEFAULT '{}' |

### 4. purchases（購入テーブル）
買い切り商品の購入記録を管理するテーブル

| カラム名 | データ型 | 説明 | 制約 |
|---------|---------|------|------|
| id | uuid | 購入ID | PRIMARY KEY, NOT NULL |
| user_id | uuid | ユーザーID | NOT NULL, REFERENCES users(id) |
| product_id | uuid | 商品ID | NOT NULL, REFERENCES products(id) |
| stripe_payment_intent_id | text | Stripe支払いID | UNIQUE, NOT NULL |
| amount | integer | 支払金額 | NOT NULL |
| status | text | ステータス（completed, refunded など） | NOT NULL |
| purchased_at | timestamp with time zone | 購入日時 | NOT NULL, DEFAULT now() |
| created_at | timestamp with time zone | 作成日時 | NOT NULL, DEFAULT now() |
| updated_at | timestamp with time zone | 更新日時 | DEFAULT now() |
| metadata | jsonb | メタデータ | DEFAULT '{}' |

### 5. payment_history（支払い履歴テーブル）
すべての支払い（サブスクリプションと買い切り両方）を記録するテーブル

| カラム名 | データ型 | 説明 | 制約 |
|---------|---------|------|------|
| id | uuid | 支払い履歴ID | PRIMARY KEY, NOT NULL |
| user_id | uuid | ユーザーID | NOT NULL, REFERENCES users(id) |
| product_id | uuid | 商品ID | NOT NULL, REFERENCES products(id) |
| subscription_id | uuid | サブスクリプションID | REFERENCES subscriptions(id) |
| purchase_id | uuid | 購入ID | REFERENCES purchases(id) |
| stripe_payment_intent_id | text | Stripe支払いID | |
| stripe_invoice_id | text | Stripe請求書ID | |
| amount | integer | 支払金額 | NOT NULL |
| payment_method | text | 支払い方法 | |
| status | text | ステータス | NOT NULL |
| paid_at | timestamp with time zone | 支払日時 | |
| created_at | timestamp with time zone | 作成日時 | NOT NULL, DEFAULT now() |
| metadata | jsonb | メタデータ | DEFAULT '{}' |

## リレーションシップ

1. users.id ← subscriptions.user_id (1対多)
2. users.id ← purchases.user_id (1対多)
3. users.id ← payment_history.user_id (1対多)
4. products.id ← subscriptions.product_id (1対多)
5. products.id ← purchases.product_id (1対多)
6. products.id ← payment_history.product_id (1対多)
7. subscriptions.id ← payment_history.subscription_id (1対多)
8. purchases.id ← payment_history.purchase_id (1対多)

## インデックス設定

- users テーブル
  - email (UNIQUE)
  - stripe_customer_id (UNIQUE)

- products テーブル
  - stripe_product_id (UNIQUE)
  - is_subscription, is_active (複合インデックス)

- subscriptions テーブル
  - user_id, product_id (複合インデックス)
  - stripe_subscription_id (UNIQUE)
  - status, current_period_end (複合インデックス)

- purchases テーブル
  - user_id, product_id (複合インデックス)
  - stripe_payment_intent_id (UNIQUE)
  - status (インデックス)

- payment_history テーブル
  - user_id (インデックス)
  - subscription_id (インデックス)
  - purchase_id (インデックス)
  - status (インデックス)
  - paid_at (インデックス)

## セキュリティポリシー

SupabaseのRLSを使用して、以下のセキュリティポリシーを実装します：

1. users テーブル
   - ユーザーは自分自身のレコードのみ参照・更新可能
   - 管理者はすべてのレコードにアクセス可能

2. products テーブル
   - 参照のみ全ユーザーに許可
   - 作成・更新・削除は管理者のみ許可

3. subscriptions テーブル
   - ユーザーは自分のサブスクリプションのみ参照可能
   - 作成・更新は管理者とシステムのみ許可

4. purchases テーブル
   - ユーザーは自分の購入履歴のみ参照可能
   - 作成・更新は管理者とシステムのみ許可

5. payment_history テーブル
   - ユーザーは自分の支払い履歴のみ参照可能
   - 作成・更新は管理者とシステムのみ許可 
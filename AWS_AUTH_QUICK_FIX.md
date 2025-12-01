# Quick Fix: AWS Authentication

## Current Issue

AWS SSO is not configured. You need to either:
1. Configure AWS SSO, OR
2. Use access keys instead

## Option 1: Configure AWS SSO (Recommended if your org uses SSO)

### Step 1: Get SSO Information

You'll need from your AWS administrator or AWS console:
- **SSO Start URL** (e.g., `https://your-company.awsapps.com/start`)
- **SSO Region** (usually `us-east-1` or `us-west-2`)
- **Account ID** (`384694315263` for your cluster)
- **Role Name** (e.g., `AdministratorAccess`, `PowerUser`, etc.)

### Step 2: Configure SSO

```bash
aws configure sso
```

You'll be prompted for:
```
SSO start URL: [Enter your SSO URL]
SSO region: [Enter region, e.g., us-east-1]
SSO account ID: 384694315263
SSO role name: [Enter role name, e.g., AdministratorAccess]
CLI default client Region: us-west-2
CLI default output format: json
```

### Step 3: Login

```bash
aws sso login
# Or with profile name
aws sso login --profile default
```

### Step 4: Verify

```bash
aws sts get-caller-identity
```

## Option 2: Use Access Keys (If SSO Not Available)

### Step 1: Get Access Keys

From AWS Console:
1. Go to IAM → Users → Your User
2. Security Credentials tab
3. Create Access Key
4. Save Access Key ID and Secret Access Key

### Step 2: Configure

```bash
aws configure
```

Enter:
- AWS Access Key ID: [your key]
- AWS Secret Access Key: [your secret]
- Default region: us-west-2
- Default output format: json

### Step 3: Verify

```bash
aws sts get-caller-identity
```

## Option 3: Use Interactive Setup Script

We've created a helper script:

```bash
cd DocEX
./scripts/setup_aws_auth.sh
```

This will guide you through the setup interactively.

## After Authentication Works

Once `aws sts get-caller-identity` succeeds:

```bash
# Update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2

# Verify cluster access
kubectl get nodes

# Continue with Argo setup
cd DocEX
./scripts/setup_argo_workflow.sh
```

## Common SSO URLs

If you're not sure of your SSO URL, common patterns:
- `https://your-company.awsapps.com/start`
- `https://your-company.signin.aws.amazon.com/console`
- Check with your AWS administrator

## Need Help?

- Check your organization's AWS access documentation
- Contact your AWS administrator for:
  - SSO Start URL
  - SSO Region
  - Account ID (we know it's `384694315263`)
  - Role name you should use

---

**Once authentication is working, everything else is ready to deploy!** 🚀



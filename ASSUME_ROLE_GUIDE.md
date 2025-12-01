# How to Use Assume Role for EKS Access

## Quick Method

You have a role ARN that should give you EKS access. Here's how to use it:

### Option 1: Use the Setup Script (Recommended)

```bash
cd DocEX
./scripts/assume_role_and_setup.sh
```

This script will:
1. Check/refresh SSO authentication
2. Assume the EKS role
3. Set environment variables
4. Update kubeconfig
5. Test cluster access

### Option 2: Manual Command (Your Original)

Run this in your terminal:

```bash
# First, make sure you're authenticated
export AWS_PROFILE=mrrahman-384694315263
aws sso login --profile mrrahman-384694315263

# Then assume the role (your exact command)
eval $(aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name eshan-session \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)

# Verify it worked
aws sts get-caller-identity

# Update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2

# Test cluster access
kubectl get nodes
```

### Option 3: Source the Script (For Current Shell)

To use the credentials in your current shell session:

```bash
cd DocEX
source <(./scripts/assume_role_and_setup.sh)
```

Or manually:

```bash
# Run the assume role command and source it
source <(aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name eshan-session \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)

# Then update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
```

## Understanding the Command

Your command does the following:

1. **`aws sts assume-role`** - Assumes the IAM role
2. **`--role-arn`** - The role to assume (has EKS permissions)
3. **`--role-session-name`** - Name for this session
4. **`--query`** - Extracts credentials and formats them as export statements
5. **`eval $(...)`** - Executes the export statements in your shell

## Credential Expiration

**Important:** These credentials expire in **1 hour** (default duration).

To refresh:
- Run the assume-role command again
- Or use the script again

## After Assuming Role

Once you have cluster access:

```bash
# Check Argo Workflows
kubectl get pods -n argo
kubectl get namespaces

# If Argo not installed, install it
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.0/install.yaml

# Continue with Argo setup
cd DocEX
./scripts/setup_argo_workflow.sh
```

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

Your base SSO role doesn't have permission to assume the EKS role. Contact your AWS administrator.

### Error: "InvalidClientTokenId"

Your SSO session expired. Re-login:
```bash
aws sso login --profile mrrahman-384694315263
```

### Error: "Cannot assume role"

Make sure:
1. You're authenticated: `aws sts get-caller-identity`
2. Your role has permission to assume the target role
3. The role ARN is correct

## Quick Reference

```bash
# 1. Authenticate
export AWS_PROFILE=mrrahman-384694315263
aws sso login --profile mrrahman-384694315263

# 2. Assume role
eval $(aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name eshan-session \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)

# 3. Update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2

# 4. Verify
kubectl get nodes
```

---

**Role ARN:** `arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec`  
**Cluster:** `exec-service-mrrahman`  
**Region:** `us-west-2`



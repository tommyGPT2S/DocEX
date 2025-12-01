# Troubleshooting Assume Role Issues

## Current Issue: "ForbiddenException: No access"

You're getting this error when trying to assume the role. This typically means:

1. **Your SSO role doesn't have permission to assume the target role**
2. **The role's trust policy doesn't allow your SSO role**
3. **SSO session has expired or has limited permissions**

## Solutions

### Solution 1: Use Access Keys Instead of SSO

If you have IAM access keys (not SSO), use those:

```bash
# Set access keys
export AWS_ACCESS_KEY_ID='your-access-key-id'
export AWS_SECRET_ACCESS_KEY='your-secret-access-key'
unset AWS_PROFILE  # Important: unset SSO profile

# Now try assuming the role
eval $(aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name eshan-session \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)

# Verify
aws sts get-caller-identity
```

### Solution 2: Request Permission from AWS Admin

Contact your AWS administrator and request:

1. **Permission for your SSO role to assume the EKS role**
   - Role ARN: `arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec`
   - Your SSO role needs `sts:AssumeRole` permission

2. **Or update the EKS role's trust policy** to allow your SSO role

### Solution 3: Use a Different Profile

Try other profiles that might have assume-role permissions:

```bash
# List all profiles
aws configure list-profiles

# Try different profiles
export AWS_PROFILE=384694315263_KSAI_Account_Admin
aws sso login --profile 384694315263_KSAI_Account_Admin

# Then try assume role
eval $(aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name eshan-session \
    --query 'Credentials.[join(`=`,[`AWS_ACCESS_KEY_ID`,AccessKeyId]), join(`=`,[`AWS_SECRET_ACCESS_KEY`,SecretAccessKey]), join(`=`,[`AWS_SESSION_TOKEN`,SessionToken])]' \
    --output text | xargs -n1 echo export)
```

### Solution 4: Check Role Trust Policy

The EKS role's trust policy might not allow your SSO role. Ask your admin to check:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::384694315263:role/YOUR_SSO_ROLE"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Solution 5: Use AWS Console to Assume Role

1. Go to AWS Console
2. Switch to the role: `exec-service-mrrahman-masters-role-70028ec`
3. Get temporary credentials from the console
4. Export them:

```bash
export AWS_ACCESS_KEY_ID='from-console'
export AWS_SECRET_ACCESS_KEY='from-console'
export AWS_SESSION_TOKEN='from-console'
unset AWS_PROFILE

# Then update kubeconfig
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
```

## Diagnostic Commands

### Check Your Current Identity

```bash
# With SSO profile
export AWS_PROFILE=mrrahman-384694315263
aws sts get-caller-identity

# Without profile (using access keys)
unset AWS_PROFILE
aws sts get-caller-identity
```

### Test Assume Role Permission

```bash
# Try to assume role and see the exact error
aws sts assume-role \
    --role-arn arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec \
    --role-session-name test-session \
    --duration-seconds 900
```

### Check What You Can Do

```bash
# List what you can do with current credentials
aws iam simulate-principal-policy \
    --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
    --action-names sts:AssumeRole \
    --resource-arns arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec
```

## Quick Test Script

```bash
# Test if you can assume the role
ROLE_ARN="arn:aws:iam::384694315263:role/exec-service-mrrahman-masters-role-70028ec"

# Try with current credentials
echo "Testing with current credentials..."
aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "test-$(date +%s)" \
    --duration-seconds 900 \
    --output json

# If that fails, the error message will tell you why
```

## Alternative: Direct EKS Access

If assume-role isn't working, you might be able to access EKS directly if your SSO role has EKS permissions:

```bash
# Try direct access without assuming role
export AWS_PROFILE=mrrahman-384694315263
aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2
kubectl get nodes
```

## Next Steps

1. **If you have access keys**: Use Solution 1
2. **If you need SSO**: Contact admin for Solution 2
3. **If you have console access**: Use Solution 5
4. **For development**: Continue using local testing (all code works locally!)

---

**Remember:** All the workflow code is complete and tested locally. You can continue development while resolving the EKS access issue!



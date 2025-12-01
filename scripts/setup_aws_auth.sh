#!/bin/bash
# Interactive script to set up AWS authentication

echo "=========================================="
echo "AWS Authentication Setup"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   brew install awscli"
    exit 1
fi

echo "Current AWS configuration:"
aws configure list
echo ""

# Check for existing profiles
echo "Available AWS profiles:"
aws configure list-profiles
echo ""

echo "Choose authentication method:"
echo "1. AWS SSO (recommended for organizations)"
echo "2. Access Keys (IAM user credentials)"
echo "3. Use existing profile"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Setting up AWS SSO..."
        echo "You'll need:"
        echo "  - SSO Start URL (e.g., https://your-org.awsapps.com/start)"
        echo "  - SSO Region (e.g., us-east-1)"
        echo "  - Account ID (e.g., 384694315263)"
        echo "  - Role name (e.g., AdministratorAccess)"
        echo ""
        read -p "Enter SSO Start URL: " sso_start_url
        read -p "Enter SSO Region: " sso_region
        read -p "Enter Account ID: " account_id
        read -p "Enter Role Name (default: AdministratorAccess): " role_name
        role_name=${role_name:-AdministratorAccess}
        read -p "Enter Profile Name (default: default): " profile_name
        profile_name=${profile_name:-default}
        
        echo ""
        echo "Configuring SSO profile: $profile_name"
        aws configure sso --profile $profile_name <<EOF
$sso_start_url
$sso_region
$account_id
$role_name
json
EOF
        
        echo ""
        echo "✅ SSO profile configured"
        echo "Now login with:"
        echo "  aws sso login --profile $profile_name"
        echo ""
        echo "Or set as default:"
        echo "  export AWS_PROFILE=$profile_name"
        echo "  aws sso login"
        ;;
        
    2)
        echo ""
        echo "Setting up Access Keys..."
        echo "You'll need:"
        echo "  - AWS Access Key ID"
        echo "  - AWS Secret Access Key"
        echo ""
        read -p "Enter Profile Name (default: default): " profile_name
        profile_name=${profile_name:-default}
        
        aws configure --profile $profile_name
        
        echo ""
        echo "✅ Access keys configured for profile: $profile_name"
        echo "To use this profile:"
        echo "  export AWS_PROFILE=$profile_name"
        ;;
        
    3)
        echo ""
        echo "Available profiles:"
        aws configure list-profiles
        echo ""
        read -p "Enter profile name to use: " profile_name
        
        export AWS_PROFILE=$profile_name
        
        # Check if it's SSO profile
        if aws configure get sso_start_url --profile $profile_name &> /dev/null; then
            echo "This is an SSO profile. Logging in..."
            aws sso login --profile $profile_name
        else
            echo "Using access key profile: $profile_name"
        fi
        
        echo ""
        echo "✅ Using profile: $profile_name"
        echo "Profile is set in current shell session"
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Verifying authentication..."
aws sts get-caller-identity

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Authentication successful!"
    echo ""
    echo "Next steps:"
    echo "1. Update kubeconfig:"
    echo "   aws eks update-kubeconfig --name exec-service-mrrahman --region us-west-2"
    echo ""
    echo "2. Verify cluster access:"
    echo "   kubectl get nodes"
    echo ""
    echo "3. Continue with Argo setup:"
    echo "   cd DocEX"
    echo "   ./scripts/setup_argo_workflow.sh"
else
    echo ""
    echo "❌ Authentication failed. Please check your credentials."
    exit 1
fi



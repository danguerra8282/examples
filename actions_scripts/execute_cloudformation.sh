# Description:  Executes either an AWS Cloudformation Create-Stack or Update-Stack command based on wither the stack already exists.
# Usage:  ./execute_cloudformation.sh %stack_name% %aws_region% %cloudformation_template_location.yml%
# Example:  ./execute_cloudformation.sh my-stack-123 us-east-1 cloudformation_folder/my-stack-123-template.yml

# CONST
ProductName="Product_Name"
Team="Team_Name"
Owner="email@place.com"
BusinessUnit="Your_Business_Unit"

# Functions
wait_for_stack_completion () {
  stack_name=$1
  region=$2

  COMPLETE=false
  while [ "$COMPLETE" == "false" ]
  do 
    result=$(/usr/local/bin/aws cloudformation describe-stacks --stack-name $stack_name --region $region)
    state=$(echo $result | jq -r '.Stacks | .[0] | .StackStatus')
    echo "state: $state"
    if [[ $state == "UPDATE_COMPLETE" ]] || [[ $state == "CREATE_COMPLETE" ]]; then
      COMPLETE=true
    elif [[ $state == "CREATE_FAILED" ]] || [[ $state == "ROLLBACK_COMPLETE" ]]; then
      echo "Cloudformation $stack_name failed with: $state"
      exit 1
    else
      echo "Waiting for $stack_name completion..."
      sleep 10
    fi
  done
}

# Main
stack_name=$1
region=$2
template=$3

# Search for Existing Stack
output=$(/usr/local/bin/aws cloudformation describe-stacks --stack-name $stack_name --region $region 2>&1 --no-cli-pager | grep -o -i "ValidationError" || echo "nope")

# Create New Stack or Update Existing Stack
if [[ $output == "ValidationError" ]]; then
    echo "Creating new cloudformation stack $stack_name ..."
    /usr/local/bin/aws cloudformation create-stack --stack-name $stack_name --template-body file://$3 --tags Key=ProductName,Value=$ProductName Key=Owner,Value=$Owner Key=Team,Value=$Team Key=BusinessUnit,Value=$BusinessUnit
    wait_for_stack_completion $stack_name $region
else
    echo "$stack_name found; updating..."
    /usr/local/bin/aws cloudformation update-stack --stack-name $stack_name --template-body file://$3 --tags Key=ProductName,Value=$ProductName Key=Owner,Value=$Owner Key=Team,Value=$Team Key=BusinessUnit,Value=$BusinessUnit &>/dev/null
    checkstack=$(echo $?)
  
    # Existing Stack Doesn't need to be Updated
    if [[ $checkstack == "254" ]]; then
        echo "$stack_name; No updates are to be performed"
    else
        wait_for_stack_completion $stack_name $region
    fi
fi

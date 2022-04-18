#!/usr/bin/env /bin/bash
#Purpose: This bash script allow users to assume allowed roles in aws 

set -eu
#set -x

errordisplay() {
  echo "Error on $1"
}
trap 'errordisplay $LINENO' ERR

trap 'rm -f "$COOKIES" && rm -f "$HEADERS"' exit 
COOKIES=$(mktemp) || (echo "Could not create temp cookies file" && exit 1)
HEADERS=$(mktemp) || (echo "Could not create temp headers file" && exit 1)

if [ ! -f "$COOKIES" ]; then  
  exit 1
fi
if [ ! -f "$HEADERS" ]; then  
  exit 1
fi

cat << EOF > $HEADERS
Host: site.domain.com
Connection: keep-alive
Pragma: no-cache
Cache-Control: no-cache
Upgrade-Insecure-Requests: 1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Sec-Fetch-Site: none
Sec-Fetch-Mode: navigate
Sec-Fetch-User: ?1
Sec-Fetch-Dest: document
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Content-Type: application/x-www-form-urlencoded
Referer: https://site.domain.com/my.policy
EOF



endpoint=""
endpoint_url=""

timeout=3600
while [[ $# -gt 0 ]]; do
 key="$1"
 case $key in 
	-s|--session-duration)
	timeout="$2"
	shift
	shift
  ;;
  --endpoint-url)
  endpoint="$2"
  shift
  shift
  ;; 
   -*|--*)
  echo "Unknow option $1"
  exit 1
  ;;
 esac 
done
printf "Session duration will be $timeout seconds.\n"

if [[ $endpoint != "" ]]; then
  endpoint_url="--endpoint-url $endpoint"  
fi


#https://gist.github.com/cdown/1163649  look in comments
urlencode() {
  local length="${#1}"
  for (( i = 0; i < length; i++ )); do
    local c="${1:i:1}"
    case $c in
      [a-zA-Z0-9.~_-]) printf "$c" ;;
    *) printf "$c" | xxd -p -c1 | while read x;do printf "%%%s" "$x";done
  esac
done
}

#Reference: Stackoverflow https://stackoverflow.com/a/7052168
#Author: https://stackoverflow.com/users/482494/chad
read_dom () {
  local IFS=\>
  read -d \< ENTITY CONTENT
}


#base64 deocode and get accounts from SAML
get_accounts () {
  local index=0  
  local SAMLDECODED=$( echo ${SAML} | base64 --decode)  
  while read_dom; do 
    #echo $ENTITY
    if [[ $ENTITY = 'saml2:AttributeValue xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion"' ]]; then
      #echo "$ENTITY => $CONTENT"    
      if [[ $CONTENT == arn:aws:* ]]; then   
        #echo "$ENTITY => $CONTENT"    
        principalarn=$(echo ${CONTENT} | cut -d"," -f1)        
        rolearn=$(echo ${CONTENT}  | cut -d"," -f2)
        accounts[index]="${CONTENT}"
        index=$((index + 1))
      fi
    fi
  done < <(echo ${SAMLDECODED})   
  if [[ $index == 0 ]]; then
    printf "No AWS Account assetions found in saml found. Exiting...\n"
    exit 1
  fi
}


sort_accounts ()  {   
  #local IFS=$'\n'  
  printf "%s\n" "${accounts[@]}" | tr ' ' '\n' | sort | tr '\n' ' '
}

get_unique_roles () {  
  #local IFS=$'\n'
  printf "%s\n" ${accounts[@]} | tr ' ' '\n' | cut -d":" -f 11 | cut -d"/" -f2 | sort | uniq | tr '\n' ' '
}


#get principal arn from account string
principalarn () {
  local value=$1  
  printf "$value" | cut -d"," -f1
}

#get rolearn from account string
rolearn () {
  local value=$1
  printf "$value" | cut -d"," -f2
}

#get role
role () {
  local value=$1
  printf "$value" | cut -d"/" -f2
}

#get account number from role arn
getaccountnum () {
  local value=$1
  printf "$value" | cut -d":" -f5
}

#get access key from aws creds json
getaccesskey () {
  local value="$1"
  printf "$value" | grep -o '"AccessKeyId":\s"[A-Za-z0-9]*"' | cut -d" " -f2 | sed 's/"//g'
}

#get secret key from aws creds jsona
getsecretkey () {
  local value="$1"
  printf "$value" | grep -o '"SecretAccessKey":\s"[A-Za-z0-9\+\\/]*"' | cut -d" " -f2 | sed 's/"//g'
}

#get session token from aws creds json
getsessiontoken () {
  local value="$1" 
  printf "$value" | grep -o '"SessionToken":\s"[A-Za-z0-9\+\\/=]*"' | cut -d" " -f2 | sed 's/"//g'
}

#fails in github actions
# #example ..."Expiration": "2021-08-26T17:04:20+00:00" ...
 getsessionexpiration() {
   local value="$1"
   local expires=$(echo session expiration $value | \
   grep -o '"Expiration":\s"\d\{4\}-\d\{2\}-\d\{2\}T\d\{2\}:\d\{2\}:\(\d\{2\}Z\|\d\{2\}\+\d\{2\}:\d\{2\}\)"')  
   printf "%s\n" "$expires" | cut -d" " -f2 | sed 's/"//g'
}

addquitoption () {
	uniqueroles+=('Quit')
}

get_saml() {

  curl -L --noproxy "*" --tlsv1.2 -H @$HEADERS -c $COOKIES $SAFESAMLURL > /dev/null 2>&1
  encodeddata="username=$(urlencode $user)&password=$(urlencode $password)&vhost=standard"
  output=$(curl -s -L --noproxy "*" --tlsv1.2 -H @$HEADERS -b $COOKIES -c $COOKIES -X POST -d $encodeddata $MYPOLICYURL \
    | grep -o "The\susername\sor\spassword\sis\snot correct. Please try again."  || echo "default")

  if [ "$output" ==  "The username or password is not correct. Please try again." ]; then
        echo $output
        $0 && exit
  fi

  SAML=$(curl -s -L --noproxy "*" -H @$HEADERS -b $COOKIES -c $COOKIES --tlsv1.2 $AWSSAMLURL \
 | sed -n 's/^.*SAMLResponse\" value\=\"//;s/\"\/><noscript.*$//;p;' )
  if [ -z "$SAML" ]; then
    echo "SAML not defined."
    exit 1
  fi
}


assumerole () {  
  local sessionduration=$1
  local rolearn=$2
  local principalarn=$3 
  #printf "%s %s %s \n" $sessionduration $rolearn $principalarn
  local creds=$(aws sts assume-role-with-saml --duration-seconds "${sessionduration}" --role-arn "$rolearn" \
      $endpoint_url \
      --principal-arn "$principalarn" --saml-assertion "$SAML" --output json 2>&1)
  if [[ $creds == *ExpiredToken* ]]; then
      get_saml && local creds=$(assumerole $sessionduration $rolearn $principalarn)
  fi
  printf "%s" "$creds"
}


processaccounts () {
  local role="$1"
  local errorcount=0
  local errorroles=()  

  for account in "${accounts[@]}"
  do
    if [[ $account == *$role* ]]; then
      
      printf '=%.0s' {1..30}
      printf "\n"
      printf "Processing $account for role $role\n"
      principalarn=$(principalarn $account)
      rolearn=$(rolearn $account)
      accountnum=$(getaccountnum $rolearn)
        #get creds as json from aws
      sessionduration=${timeout}
     
      creds=$(assumerole $sessionduration $rolearn $principalarn)   
      rc=$?      
      if [[ $rc == 99 ]]; then
          echo "expired token"
          get_saml && creds=$(assumerole $sessionduration $rolearn $principalarn)
      fi    
      
      #creds=$(aws sts assume-role-with-saml --duration-seconds "${sessionduration}" --role-arn "$rolearn" \
      #--principal-arn "$principalarn" --saml-assertion "$SAML" --output json 2>&1)
      #printf "creds=$creds\n"  
      

      #if [ $? -ne 0 ]; then        
      #  errorroles[$errorcount]="${rolearn}"
      #  errorcount=$((errorcount + 1))
      #  printf "failed to login in with $rolearn\n"
      #  continue
      #fi
     
      local accesskey=$(getaccesskey "$creds")
      local secretkey=$(getsecretkey "$creds")
      local sessiontoken=$(getsessiontoken "$creds")
      local expires=$(getsessionexpiration "$creds")
      

      #needed to get alias
      export AWS_ACCESS_KEY_ID=$accesskey
      export AWS_SECRET_ACCESS_KEY=$secretkey
      export AWS_SESSION_TOKEN=$sessiontoken	    	    
                  
      aliasraw=$(aws iam list-account-aliases --output json | sed -n 3p | xargs)      
      alias=$(printf "%s-%s" "$aliasraw" "$role")

      unset AWS_ACCESS_KEY_ID
      unset AWS_SECRET_ACCESS_KEY
      unset AWS_SESSION_TOKEN
      
      printf "\nConfiguring session for %s which expires at %s\n" "$alias" "$expires"

      aws configure set region "us-east-1" --profile ${alias}
      aws configure set aws_access_key_id $accesskey --profile ${alias}
      aws configure set aws_secret_access_key $secretkey --profile ${alias}
      aws configure set aws_session_token $sessiontoken --profile ${alias}
      aliaslist[aliasindex]="$alias|$accountnum|$expires"
      aliasindex=$((aliasindex + 1))
    fi

#    aws ec2 describe-instances --filter Name=tag-key,Values=Name \
#    --query 'Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key==`Name`]|[0].Value,State:State.Name, PrivateIP:PrivateIpAddress, PublicIP:PublicIpAddress}' \
#    --output table
#    echo "S3 Buckets:"
#    aws s3 ls
     #exit 0
  done
  if [[ $errorcount > 0 ]]; then      
      for errorrole in "${errorroles[@]}"
      do
        printf "Error assuming $errorroles\n"
      done
  fi
  
  printf "List of Alias and related account numbers for role $role\n"
  printf "\n"
  printf "%s\n" "${aliaslist[@]}" | column -s "|" -t
  printf "Append --profile <alias> to your aws cli commands to use.\n"
}




read -p "User " user
read -s -p "Password " password


SAFESAMLURL="https://site.domain.com"
MYPOLICYURL="https://site.domain.com/my.policy"
AWSSAMLURL="https://site.domain.com/saml/idp/res?id=/Common/AWS.res"



accounts=()
aliaslist=("alias|account number|expiration" "=====|==============|==========")
aliasindex=2

printf "\n"



#curl -vvv -k -L --noproxy "*" -H @$HEADERS -b cookies -c cookies --tlsv1.2 $awssamlurl

#rm cookies.txt
#echo $SAML
#exit


get_saml   
get_accounts
accounts=($(sort_accounts))
uniqueroles=($(get_unique_roles))
addquitoption


if [[ ${#uniqueroles[@]} > 1 ]]; then
  PS3="role? "	
  select role in "${uniqueroles[@]}"; do
    if [ -n "${role}" ]; then
      if [[ $role == "Quit" ]]; then
            exit 0
      fi	      
      processaccounts $role
    fi
    PS3=""
    echo junk | select role in "${uniqueroles[@]}"; do break; done
    PS3="role? "
  done
else
      for role in "$uniqueroles[@]}"; do	
        processaccounts	$role
      done
fi

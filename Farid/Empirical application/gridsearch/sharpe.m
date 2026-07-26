%this short program computes the Sharpe ratio for the threshold
%autoregressive model

%first we calculate the mean; first we specify whether the model has drift
rf = 0 ; %risk free interest rate
drift = 1 %The drift parameter can only take values 1 or 0.  1 if there is drift
sigmae = (0.0427)^2; %this indicates the variance of the error term
% first we specify the paramters of the model including probabilities
alpha = 0.0212; %the value of the drift term
states = 3; %number of states
pi = zeros(states,1);
beta = zeros(states,1);
pi(1,1) = 0.0245; pi(2,1) = 0.1135; pi(3,1) = 1 - pi(1,1)-pi(2,1); %this specifies the probabilities of the 3 states with the first state being mean reverting, second efficient and third explosive
beta(1,1) = -0.012; beta(2,1) = 0; beta(3,1) = -0.002; % this specifies the values of the betas in the same order as the probabilities
%% CONDITIONS FOR EXISTENCE OF MOMENTS
%In this section we check whether the moment conditions are satisfied
%in the next step we calculate sum(pij*betaj)
sum1 = 0;
sum1 = beta'*pi
sum2 = 0; %this is the sum of pij*bj^2
sum2 = beta.^2'*pi
if (1-sum2)<0
    display('The Moments do not exist and a sharpe ratio cannot be calculated')
else
    

%% MEAN OF THRESHOLD MODEL
if drift == 0
    mean = 0;
else
    mean = alpha/(1-sum1);
end

%% VARIANCE OF THRESHOLD MODEL
%In order to find the variance we need to find some preliminary statistics

sum3 = (sum2 - sum1^2)/((1-sum1)^2); %this is a term we need to evaluate variance
additional = (1+(alpha^2/sigmae)*sum3); %this is the additional term when process has a drift
if drift == 0
    variance = sigmae/(1-sum2);
else
    variance = (sigmae/(1-sum2))*additional;
end

mean
variance
stdev = sqrt(variance)
sharpratio = (mean-rf)/sqrt(variance)
end


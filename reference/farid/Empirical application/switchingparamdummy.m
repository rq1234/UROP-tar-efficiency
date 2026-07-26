function [parameters] = switchingparamdummy(y,z)
%This function finds parameters for a switching regression where one state
%is a random walk with parameter equal to 1. 
%Y is the switching series for which parameters need to be found while Z is
%the forcing variable or the sentiment index
length = prod(size(y));
val = 1000; %gridspace length
iterations = (val*(val+1))/2 - val;
range = linspace(0.95,1.05,val); %this declares the range in which we look for the second and third parameter values
c1 = 1; %the random walk state
c2 = range(1); %the 2nd state (mean reverting)
c3 = range(2); %the 3rd state (explosive)
e = zeros(length,1); %the error term
parameters.p = [c1; c2; c3]; %parameter vector
parameters.minssr = 10000000000; % we have to begin by setting the sum of square residuals to a high value initially
%% The following section finds the values which minimize the sum of squared residuals
tic
for i = 1:(prod(size(range))-1) %this part of the loop sets the value of the mean reverting parameter
    c2 = range(i);
    j = i+1;
    k = j;
    for k = j:(prod(size(range))) %the second loop ensures that c2 < c3 thereby reducing the number of loops
        c3 = range(k); %this sets the value of the third parameter to a value that is greater than c2
        for m = 2:length
            if z(m)==2 %criteria for mean reversion
             beta = c2;
            elseif z(m)==1 %criteria for explosivity
             beta = c3;
            else
             beta = c1; %random walk
            end
         e(m,1) = y(m)-beta*y(m-1); %this step calculates the error term
        end
        ssr = sum(e.^2); %sum of square residuals
        if ssr<parameters.minssr %this condition checks if we need to adjust the minimum ssr value as stored in the loop
            parameters.minssr = ssr;
            parameters.p = [c1 c2 c3]; %this vector stores the parameter values where we achieve the minimum ssr
        else
            parameters.minssr = parameters.minssr;
        end
    end
end
parameters.minssr;
parameters.p;
toc
end



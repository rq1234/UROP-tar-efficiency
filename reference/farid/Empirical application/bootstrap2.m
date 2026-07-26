%This uses a different method for bootstrapping
%We begin by spliting our data into 3 sub-samples and then using a
%numerical procedure on the second and 3rd sub-sample. 
function [beta2] = bootstrap2(y,z)
count = zeros(3,1);
length = prod(size(y));
bootstraps = 1000;
%The loop below counts the number of entries in each state
for i = 1:length
    if z(i)<70
        count(2,1)=count(2,1)+1;
    elseif z(i) > 99
        count(3,1) = count(3,1)+1;
    else
        count(1,1) = count(1,1)+1;
    end
end
c2 = 1; c3 = 1;
%Next we create the split samples
y1 = zeros(count(1,1),1);
y2 = zeros(count(2,1),1);
y3 = zeros(count(3,1),1);
k1 = 0; k2 = 0; k3=0;

%Now we will the split samples with actual values

for j = 1:length
    if z(j)<70
        k2 = k2+1;
        y2(k2) = y(j,1);
    elseif z(j)>99
        k3 = k3+1;
        y3(k3) = y(j,1);
    else
        k1 = k1+1;
        y1(k1) = y(j,1);
    end
end
mdl2 =fitlm(y2(1:(count(2,1)-1)),y2(2:count(2,1)),'Intercept',false)
mdl3 =fitlm(y3(1:(count(3,1)-1)),y3(2:count(3,1)),'Intercept',false)
beta2 = zeros(2,bootstraps);
%% This section starts the bootstrapping procedure for the explosive and mean reverting states
%First we bootstrap the mean-reverting state

%for j = 1: bootstraps
minssr=100000000000000; i = 1; j=1; m =1;
e2 = zeros(count(2,1),1);
e3 = zeros(count(3,1),1);

val = 1000;
range = linspace(0.9,1.1,val);
for i = 1:prod(size(range))
    c2 = range(i);
    for m = 2:(prod(size(y2)))
        e2(m,1)=y2(m)-c2*y2(m-1);
    end
    ssr = sum(e2.^2); %sum of squared residuals
        if ssr<minssr %this condition checks if we need to adjust the minimum ssr value as stored in the loop
            minssr = ssr;
            beta2(1,j) = c2;
        else
            minssr = minssr;
        end
end

i = 1; m=1; minssr = 100000000000; %re-initialize for explosive regression
range = linspace(c2,1.1,val);
for i = 1:prod(size(range))
    c3 = range(i);
    for m = 2:(prod(size(y3)))
        e3(m,1)=y3(m)-c3*y3(m-1);
    end
    ssr = sum(e3.^2); %sum of squared residuals
        if ssr<minssr %this condition checks if we need to adjust the minimum ssr value as stored in the loop
            minssr = ssr;
            beta2(2,j) = c3;
        else
            minssr = minssr;
        end
        
end
%end
end

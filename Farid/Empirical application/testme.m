function [test1] = testme(y,z);
count = zeros(3,1);
length = prod(size(y));
for i = 1:length
    if z(i)<70
        count(2,1)=count(2,1)+1;
    elseif z(i) > 99
        count(3,1) = count(3,1)+1;
    else
        count(1,1) = count(1,1)+1;
    end
end

y1 = zeros(count(1,1),1);
y2 = zeros(count(2,1),1);
y3 = zeros(count(3,1),1);
k1 = 0; k2 = 0; k3=0;
count
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

y1;
y2;
y3;

mdl1 =fitlm(y1(1:(count(1,1)-1)),y1(2:count(1,1)),'Intercept',false)
mdl2 =fitlm(y2(1:(count(2,1)-1)),y2(2:count(2,1)),'Intercept',false)
mdl3 =fitlm(y3(1:(count(3,1)-1)),y3(2:count(3,1)),'Intercept',false)
end

        
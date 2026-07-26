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

for j = 1:length
    if z(i)<70
        k2 = k2+1;
        y2(k2) = y(i,1);
    elseif z(i)>99
        k3 = k3+1;
        y3(k3) = y(i,1);
    else
        k1 = k1+1;
        y1(k1) = y(i,1);
    end
end

y1
y2
y3
end

        
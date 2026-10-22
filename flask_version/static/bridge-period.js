function bridgePeriodDates(period, now=new Date()) {
    if(period==='custom')return null;
    const format=date=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    const end=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    if(period==='all')return {from:'1970-01-01',to:format(end)};
    if(!['1','3','6','12'].includes(period))return null;
    const start=new Date(end.getFullYear(),end.getMonth()-Number(period),1);
    const lastDay=new Date(start.getFullYear(),start.getMonth()+1,0).getDate();
    start.setDate(Math.min(end.getDate(),lastDay));
    return {from:format(start),to:format(end)};
}

function bindBridgePeriod() {
    const period=document.querySelector('[name="bridge-period"]');
    if(!period)return;
    const from=document.querySelector('[name="bridge-from"]');
    const to=document.querySelector('[name="bridge-to"]');
    const apply=()=>{
        const dates=bridgePeriodDates(period.value);
        if(dates){from.value=dates.from;to.value=dates.to;}
    };
    period.addEventListener('change',apply);
    for(const field of [from,to])field.addEventListener('input',()=>{period.value='custom';});
    apply();
}
document.addEventListener('DOMContentLoaded',bindBridgePeriod);

function balanceCurveBounds(curves){
    let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
    for(const curve of curves)for(const [x,y] of curve.points){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
    if(!Number.isFinite(minX))return null;
    if(maxX===minX)maxX=minX+86400;
    const padding=Math.max((maxY-minY)*.06,1);
    return {minX,maxX,minY:minY-padding,maxY:maxY+padding};
}

class GeraSetCurvePlot {
    constructor(root){
        this.root=root;this.curves=new Map();this.selected='';this.frame=null;
        const heading=document.createElement('h3');heading.textContent='Curvas de saldo por passe';
        this.count=document.createElement('p');
        this.canvas=document.createElement('canvas');this.canvas.className='bridge-curves-canvas';this.canvas.setAttribute('role','img');
        this.canvas.setAttribute('aria-label','Curvas de saldo realizado por data, uma linha por passe de otimização');
        const controls=document.createElement('div');controls.className='bridge-report-pages';
        const label=document.createElement('label');label.textContent='Destacar passe: ';
        this.input=document.createElement('input');this.input.type='text';this.input.inputMode='numeric';this.input.placeholder='Melhor saldo final';label.appendChild(this.input);
        const button=document.createElement('button');button.type='button';button.className='btn';button.textContent='Destacar';
        button.addEventListener('click',()=>{this.selected=this.input.value.trim();this.schedule();});
        this.details=document.createElement('p');
        const note=document.createElement('p');note.className='muted';
        note.textContent='Saldo realizado, incluindo custos. Até 128 pontos reais por passe; amostragem pode ocultar variações intermediárias. As curvas chegam após cada passe concluir.';
        controls.append(label,button);root.replaceChildren(heading,this.count,this.canvas,controls,this.details,note);
        this.resize=new ResizeObserver(()=>this.schedule());this.resize.observe(root);
        this.schedule();
    }
    add(curves){for(const curve of curves)this.curves.set(curve.pass,curve);this.schedule();}
    schedule(){if(this.frame===null)this.frame=requestAnimationFrame(()=>{this.frame=null;this.draw();});}
    destroy(){this.resize.disconnect();if(this.frame!==null)cancelAnimationFrame(this.frame);}
    draw(){
        const curves=[...this.curves.values()],bounds=balanceCurveBounds(curves);
        this.count.textContent=curves.length?`${curves.length.toLocaleString('pt-BR')} passes com curvas recebidas`:'Aguardando o primeiro passe concluir e enviar sua curva...';
        const width=Math.max(300,Math.floor(this.root.clientWidth)),height=400,dpr=Math.min(window.devicePixelRatio||1,2);
        this.canvas.width=width*dpr;this.canvas.height=height*dpr;
        const ctx=this.canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.fillStyle='#fff';ctx.fillRect(0,0,width,height);
        if(!bounds)return;
        const left=86,right=22,top=20,bottom=48;
        const x=value=>left+(value-bounds.minX)/(bounds.maxX-bounds.minX)*(width-left-right);
        const y=value=>height-bottom-(value-bounds.minY)/(bounds.maxY-bounds.minY)*(height-top-bottom);
        ctx.font='12px Segoe UI';ctx.lineWidth=1;
        for(let i=0;i<=4;i++){
            const value=bounds.minY+(bounds.maxY-bounds.minY)*i/4,yy=y(value);
            ctx.strokeStyle='#e5e7eb';ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(width-right,yy);ctx.stroke();
            ctx.fillStyle='#64748b';ctx.textAlign='right';ctx.fillText(value.toLocaleString('pt-BR',{maximumFractionDigits:2}),left-8,yy+4);
            const time=bounds.minX+(bounds.maxX-bounds.minX)*i/4,xx=x(time);
            ctx.textAlign=i===0?'left':i===4?'right':'center';
            ctx.fillText(new Date(time*1000).toLocaleDateString('pt-BR',{timeZone:'UTC'}),xx,height-18);
        }
        const best=curves.reduce((a,b)=>b.points.at(-1)[1]>a.points.at(-1)[1]?b:a);
        const selected=this.curves.get(this.selected)||best;
        function line(curve,color,size){ctx.strokeStyle=color;ctx.lineWidth=size;ctx.beginPath();curve.points.forEach(([t,b],index)=>{if(index)ctx.lineTo(x(t),y(b));else ctx.moveTo(x(t),y(b));});ctx.stroke();}
        curves.forEach((curve,index)=>line(curve,`hsla(${(index*137.508)%360},70%,45%,${curves.length>100?.12:.45})`,1));
        line(selected,'#155eef',2.5);
        const final=selected.points.at(-1)[1];
        this.details.textContent=`Destaque: passe ${selected.pass} · saldo final ${final.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})} · ${selected.trades} negociações`;
        if(this.selected&&!this.curves.has(this.selected))this.details.textContent+=' · Passe solicitado ainda não recebido; exibindo o maior saldo final.';
    }
}

export function TopNav({children}) {
    return (
        <div className="absolute justify-center top-4 left-4 right-4 z-10 flex items-center">
            <div className={`h-20 max-w-[40%] flex gap-3 pl-5 pr-5 pt-2 pb-2 z-10 bg-white/20
             backdrop-blur-sm rounded-2xl border border-white justify-center
                drop-shadow-2xl`}>
                {children}
            </div>
        </div>
    )
}
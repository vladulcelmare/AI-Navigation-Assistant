import {useEffect, useState, useRef} from 'react';
import {useAuth} from '../features/auth/AuthContext.jsx';

export function Login({setMode}) {
    const [email, setEmail] = useState('test_user@example.com');
    const [password, setPassword] = useState('parola123');
    const [error, setError] = useState('');
    const auth = useAuth();

    return (
        <div className="w-full max-w-sm p-6 bg-[#ff000000] uppercase font-ndot2 transition-all duration-300 ease-in-out text-white">
            <h2 className="text-2xl font-semibold mb-4 font-ndot2 text-white">
                LOGIN
            </h2>
            <div className="mb-4">
                <label htmlFor="login-email" className="block text-sm font-medium text-white font-ndot">
                    Email
                </label>
                <input
                    id="login-email"
                    type="email"
                    value={email}
                    placeholder="Email"
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full mt-1 p-2 rounded bg-transparent border border-white text-white"
                />

                <label htmlFor="password" className="block text-sm font-medium text-white font-ndot mt-3">
                    Password
                </label>
                <input
                    id="password"
                    type="password"
                    value={password}
                    placeholder="Password"
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full mt-1 p-2 rounded bg-transparent border border-white text-white"
                />
                <div className="text-sm font-bold font-lettera text-red underline mt-3 animate-pulse">
                    {error}
                </div>
                <button
                    onClick={()=> {
                        setError('');
                        auth.login(email, password).catch((err) => {
                            setError(err.message);
                        })
                    }}
                    className="w-full py-2 px-4 border border-white text-white rounded hover:inset-shadow-sm hover:inset-shadow-white duration-300 transition ease-in-out mt-4"
                >
                    Login
                </button>

                <div className="mt-3 text-white">
                    Don't have an account?{' '}
                    <button
                        onClick={() => setMode('register')}
                        className="text-blue-300 hover:underline transition duration-300 ease-in-out"
                    >
                        Register
                    </button>
                </div>
            </div>
        </div>
    );
}

export function Register({setMode}) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [email, setEmail] = useState('');
    const [ageGroup, setAgeGroup] = useState('');
    const [driverType, setDriverType] = useState('');
    const [roadCondition, setRoadCondition] = useState('');
    const [tolls, setTolls] = useState('');
    const [error, setError] = useState('');
    const hasError = error !== "";
    const auth = useAuth();
    return (
        <div className="w-full max-w-sm p-6 text-white font-ndot2 uppercase transition-all duration-300 ease-in-out">
            <h2 className="text-2xl font-semibold mb-4">Register</h2>
            <div className="mb-4">
                <label htmlFor="reg-username"
                       className={`block text-sm font-medium 
                            ${(!username && hasError) ? "text-red-700" : "text-white"}
                            `
                       }
                >
                    Username
                </label>
                <input
                    id="reg-username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className={
                        `w-full mt-1 p-2 rounded border 
                        ${(!username && hasError)?"border-red-700":"border-gray-300"}` // red if username is left empty and there is an error
                    }
                />

                <label htmlFor="reg-password"
                       className={`block text-sm font-medium mt-3
                        ${(!password && hasError) ? "text-red-700" : "text-white"}
                       `
                       }
                >
                    Password
                </label>
                <input
                    id="reg-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={
                        `w-full mt-1 p-2 rounded border 
                        ${(!password && hasError) ? "text-red-700" : "text-white"}`
                    }
                />

                <label htmlFor="confirmPassword"
                       className={`block text-sm font-medium mt-3
                                    ${((!confirmPassword || confirmPassword !== password) && hasError) ? "text-red-700" : "text-white"}`
                       }>
                    Confirm Password
                </label>
                <input
                    type="password"
                    id="confirmPassword"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={
                        `w-full mt-1 p-2 rounded border 
                        ${((!confirmPassword || confirmPassword !== password) && hasError) ? "text-red-700" : "text-white"}`
                    }
                />

                <label htmlFor="email" className={
                    `block text-sm font-medium mt-3 
                    ${(!email && hasError) ? "text-red-700" : "text-white"}`
                }>
                    Email
                </label>
                <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className={
                        `w-full mt-1 p-2 rounded border 
                        ${(!email && hasError) ? "text-red-700" : "text-white"}`
                    }
                />

                <label htmlFor="age-group" className="block text-sm font-medium mt-3">
                    What is your age group?
                </label>
                <select
                    id="age-group"
                    value={ageGroup}
                    onChange={(e) => setAgeGroup(e.target.value)}
                    className="w-full mt-1 p-2 rounded border [&>option]:bg-gray-800 [&>option]:text-white"
                >
                    <option value="">Select an age group</option>
                    <option value="young">Young (18-29)</option>
                    <option value="adult">Adult (30-59)</option>
                    <option value="senior">Senior (60+)</option>
                </select>

                <label htmlFor="driver-type" className="block text-sm font-medium mt-3">
                    How would you describe your driving style?
                </label>
                <select
                    id="driver-type"
                    value={driverType}
                    onChange={(e) => setDriverType(e.target.value)}
                    className="w-full mt-1 p-2 rounded border [&>option]:bg-gray-800 [&>option]:text-white"
                >
                    <option value="">Select a driving style</option>
                    <option value="calm">Calm</option>
                    <option value="fast">Fast</option>
                    <option value="efficient">Efficient</option>
                </select>

                <label htmlFor="road-condition" className="block text-sm font-medium mt-3">
                    Which roads do you usually drive on?
                </label>
                <select
                    id="road-condition"
                    value={roadCondition}
                    onChange={(e) => setRoadCondition(e.target.value)}
                    className="w-full mt-1 p-2 rounded border bg-transparent [&>option]:bg-gray-800 [&>option]:text-white"
                >
                    <option value="">Select road conditions</option>
                    <option value="highway_roads">Highway roads</option>
                    <option value="city_roads">City roads</option>
                    <option value="dirt_roads">Dirt roads</option>
                    <option value="mixed">A mix of roads</option>
                </select>

                <label htmlFor="tolls" className="block text-sm font-medium mt-3">
                    Are toll roads acceptable?
                </label>
                <select
                    id="tolls"
                    value={tolls}
                    onChange={(e) => setTolls(e.target.value)}
                    className="w-full mt-1 p-2 rounded border bg-transparent [&>option]:bg-gray-800 [&>option]:text-white"
                >
                    <option value="">Select an option</option>
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                </select>

                <div>
                    {error}
                </div>

                <button
                    onClick={
                        async () => {
                            try {
                                const result = await auth.register(
                                    username,
                                    email,
                                    password,
                                    confirmPassword,
                                    {
                                        age_group: ageGroup,
                                        driver_type: driverType,
                                        road_conditions: [roadCondition],
                                        tolls: tolls === 'true',
                                    }
                                )

                                console.log("result ", result);
                                setMode("login");
                            } catch (err) {
                                setError(err.message);
                            }
                        }
                    }
                    className="w-full py-2 px-4 border border-white text-white rounded hover:inset-shadow-sm hover:inset-shadow-white duration-300 transition ease-in-out mt-4"
                >
                    Register
                </button>

                <div className="mt-3">
                    Already have an account?{' '}
                    <button
                        onClick={() => setMode('login')}
                        className="text-blue-500 hover:underline transition duration-300 ease-in-out"
                    >
                        Login
                    </button>
                </div>
            </div>
        </div>
    );
}

export function LoginCard() {
    const [mode, setMode] = useState('login');
    const [coords, setCoords] = useState({x: 0, y: 0});
    const cardRef = useRef(null);

    const [isVisible, setIsVisible] = useState(true);
    const timeoutRef = useRef(null);

    useEffect(() => {
        const handleMouseMove = (event) => {
            const card = cardRef.current;
            if (!card) return;
            const rect = card.getBoundingClientRect();

            const localX = event.clientX - rect.left;
            const localY = event.clientY - rect.top;

            const x = Math.max(0, Math.min(localX, rect.width));
            const y = Math.max(0, Math.min(localY, rect.height));

            setCoords({ x, y });
        };

        window.addEventListener('mousemove', handleMouseMove);
        return () => window.removeEventListener('mousemove', handleMouseMove);
    }, []);

    const handleSetMode = (newMode) => {
        setIsVisible(false);
        timeoutRef.current = setTimeout(() => {
            setMode(newMode);
            setIsVisible(true);
            timeoutRef.current = null;
        }, 300);
    };

    useEffect(() => {
        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, []);

    return (
        <>
            <div className={`relative transition-all duration-300 ease-in-out 
            ${isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-10/12'}`}>
                <div
                    ref={cardRef}
                    className="relative p-6 border-2 border-white/30 rounded-3xl inset-shadow-sm
                                inset-shadow-white/15 overflow-hidden
                              bg-white/5 backdrop-blur-xs backdrop-saturate-110 m-20">
                    <div
                        className="absolute w-[200px] h-[200px] rounded-full z-[-5] blur-2xl opacity-45"
                        style={{
                            left: `${coords.x}px`,
                            top: `${coords.y}px`,
                            transform: 'translate(-50%, -50%)',
                            background: 'radial-gradient(circle, #FFFFFF, #FFFFFF00)',
                        }}
                    />
                    {mode === 'login' ? <Login setMode={handleSetMode} /> : <Register setMode={handleSetMode} />}
                </div>
            </div>
        </>
    );
}